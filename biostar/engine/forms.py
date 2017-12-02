import copy
from django import forms
from django.db.models import Q
import hjson
from . import models, auth, factory
from . import tasks
from .const import *
from .models import Project, Data, Analysis, Job, Access
from biostar.accounts.models import Profile, User

# Share the logger with models.
logger = models.logger


def join(*args):
    return os.path.abspath(os.path.join(*args))



class ProjectForm(forms.ModelForm):
    image = forms.ImageField(required=False)

    class Meta:
        model = Project
        fields = ['name', 'summary', 'text', 'image', "privacy", "sticky"]


class DataUploadForm(forms.ModelForm):
    # choices = DATA_TYPES.items()
    # data_type = forms.IntegerField(widget=forms.Select(choices=choices))

    file = forms.FileField()

    class Meta:
        model = Data
        fields = ['file', 'summary', 'text', "sticky"]


class DataEditForm(forms.ModelForm):
    # choices = DATA_TYPES.items()
    # data_type = forms.IntegerField(widget=forms.Select(choices=choices))

    class Meta:
        model = Data
        fields = ['name', 'summary', 'text', 'sticky']


class AnalysisEditForm(forms.ModelForm):
    class Meta:
        model = Analysis
        fields = ['name', "image", 'text', "summary", 'sticky']


class JobEditForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['name', "image", 'text', 'sticky']


class ChangeUserAccess(forms.Form):

    def __init__(self, project, users, hidden_users=None, *args, **kwargs):

        self.project= project
        self.users= users
        self.hidden_users = hidden_users
        self.project_users = {}

        # Data dictionary of current users used to check validity later on
        for access in self.project.access_set.filter(access__gt=Access.NO_ACCESS).all():
            user = access.user
            uid = Profile.objects.filter(user=user).first().uid
            self.project_users[uid] = access.access

        super().__init__(*args, **kwargs)

        # Create the dynamic field from each user in the users list.
        access_fields = auth.access_fields(users=self.users, project=project)
        for user_uid, field in access_fields:
            self.fields[user_uid] = field


    def save(self):

        cleaned_data = self.clean()

        for uid, access in cleaned_data.items():
            user = Profile.objects.filter(uid=uid).first().user

            # Update existing users access
            if uid in self.project_users:
                user.access_set.update(project=self.project, access=access)

            # Create new access ( or changing NO_ACCESS to something)
            else:
                current_access = user.access_set.filter(project=self.project)

                # Change existing NO_ACCESS
                if current_access:
                    current_access.update(project=self.project, access=access)
                # Create new access instance for user
                else:
                    user.access_set.create(project=self.project, access=access)
        return


    def clean(self):

        #cleaned_data = super(ChangeUserAccess, self).clean()
        #
        cleaned_data = self.project_users.copy()
        for k in self.data:
            if "csrf" not in k:
                try:
                    cleaned_data[k] = int(self.data[k])
                except:
                    raise forms.ValidationError("Invalid Type")

        # Makes sure one admin user per project
        if Access.ADMIN_ACCESS not in cleaned_data.values():
            raise forms.ValidationError("Atleast one admin user required per project")

        return cleaned_data


class DataCopyForm(forms.Form):

    paths = forms.CharField(max_length=256)

    def __init__(self, project, job=None, *args, **kwargs):
        self.project = project
        self.job = job
        super().__init__(*args, **kwargs)

    def process(self):
        # More than one can be selected
        paths = self.data.getlist('paths')
        basedir = '' if not self.job else self.job.path

        for path in paths:
            # Figure out the full path based on existing data
            if path.startswith("/"):
                path = path[1:]
            path = join(basedir, path)

            tasks.copier(target_project=self.project.id, fname=path, link=True)

            logger.info(f"Copy data at: {path}")

        return len(paths)


class AnalysisCopyForm(forms.Form):
    projects = forms.IntegerField()

    def __init__(self, analysis, *args, **kwargs):
        self.analysis = analysis
        super().__init__(*args, **kwargs)

    # TODO: refractor asap; does not need to be a list only one is picked
    def process(self):
        projects = self.data.getlist('projects')
        project_id = projects[0]

        if project_id == "0":
            return projects, None

        current_project = Project.objects.filter(id=project_id).first()

        current_params = auth.get_analysis_attr(analysis=self.analysis, project=current_project)
        new_analysis = auth.create_analysis(**current_params)

        # Images needs to be set by it set
        new_analysis.image.save(self.analysis.name, self.analysis.image, save=True)
        new_analysis.name = f"Copy of: {self.analysis.name}"
        new_analysis.state = self.analysis.state
        new_analysis.security = self.analysis.security
        new_analysis.save()

        return projects, new_analysis


class RecipeInterface(forms.Form):

    name = forms.CharField(max_length=256, help_text="This is will be the name of the results.")

    def __init__(self, request, project, json_data, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # The json data determines what fields does the form have.
        self.json_data = json_data

        # The project is required to select data from.
        self.project = project

        # Get request specific information
        self.request = request
        self.user = self.request.user

        # Create the dynamic field from each key in the data.
        for name, data in self.json_data.items():
            field = factory.dynamic_field(data, self.project)

            # Insert only valid fields.
            if field:
                self.fields[name] = field

    def clean(self):
        cleaned_data = super(RecipeInterface, self).clean()
        msg = "You don't have sufficient access rights to execute this analysis."
        if self.user.is_anonymous():
            raise forms.ValidationError(msg)
        entry = Access.objects.filter(user=self.user, project=self.project).first()
        if not entry or entry.access < Access.EXECUTE_ACCESS:
            raise forms.ValidationError(msg)

    def fill_json_data(self):
        """
        Produces a filled in JSON data based on user input.
        Should be called after the form has been filled and is valid.
        """

        # Creates a data.id to data mapping.
        store = dict((data.id, data) for data in self.project.data_set.all())

        # Make a copy of the original json data used to render the form.
        json_data = copy.deepcopy(self.json_data)

        # Alter the json data and fill in the extra information.
        for field, item in json_data.items():

            # If the field is a data field then fill in more information.
            if item.get("path") or item.get("link"):
                data_id = int(self.cleaned_data.get(field))
                data = store.get(data_id)

                # This mutates the `item` dictionary!
                data.fill_dict(item)

            # The JSON value will be overwritten with the selected field value.
            if field in self.cleaned_data:
                item["value"] = self.cleaned_data[field]

        return json_data


class EditCode(forms.Form):
    SAVE = "SAVE"

    # Determines what action to perform on the form.
    action = forms.CharField()

    # The script template.
    template = forms.CharField(required=False)

    # The json specification.
    json = forms.CharField(required=False)

    def __init__(self, user, project, *args, **kwargs):
        self.user = user
        self.project = project
        super().__init__(*args, **kwargs)

    def clean_json(self):
        cleaned_data = super(EditCode, self).clean()
        json_text = cleaned_data.get("json")
        try:
            hjson.loads(json_text)
        except Exception as exc:
            msg = f"Invalid json: {exc}"
            raise forms.ValidationError(msg)
        return json_text

    def clean(self):
        cleaned_data = super(EditCode, self).clean()
        action = cleaned_data.get("action")

        if action == self.SAVE:
            msg = "You don't have sufficient access rights to overwrite this entry."
            if self.user.is_anonymous():
                raise forms.ValidationError(msg)
            entry = Access.objects.filter(user=self.user, project=self.project).first()
            if not entry or entry.access < Access.EDIT_ACCESS:
                raise forms.ValidationError(msg)
