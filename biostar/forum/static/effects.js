function move_post(parent_elem, source_elem) {

    var parent = parent_elem.data("value");
    var source = source_elem.data("value");

    $.ajax('/drag/and/drop/',
        {
            type: 'POST',
            dataType: 'json',
            ContentType: 'application/json',
            data: {
                'uid': source,
                'parent': parent,
            },
            success: function (data) {

                if (data.status === 'error') {
                    popup_message(parent_elem, data.msg, data.status, 2000);
                } else {
                    //alert(data.status);
                    source_elem.transition('zoom');
                    window.location.reload();
                    popup_message(parent_elem, "Moved Post", 'success', 2000);
                }
            },
            error: function (xhr, status, text) {
                error_message(parent_elem, xhr, status, text);
            }
        });

}

function remoteSearch(text, cb) {
    if (text.length === 0) {
        return
    }
    var URL = "/ajax/handle/search/";
    xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                var data = JSON.parse(xhr.responseText);
                var vals = $.map(data.users, function (value) {
                    return {
                        key: value,
                        name: value,
                    };
                });
                cb(vals);

            } else if (xhr.status === 403) {
                cb([]);
            }
        }
    };
    xhr.open("GET", URL + "?query=" + text, true);
    xhr.send();
}


function autocomplete_users() {
    // Add autocomplete to any text area element with autocomplete tag.
    var autocomplete = $('.autocomplete');

    var tribute = new Tribute({
        values: function (text, cb) {
            remoteSearch(text, cb);
        },

        menuItemLimit: 5,
        selectTemplate: function (item) {
            return '@' + item.original.name;

        },
        menuItemTemplate: function (item) {
            let url = '/ajax/user/image/{0}/'.format(item.original.name);
            return "<img class='ui circular image' style='display:inline' src='{0}'  height='20' width='20' /><b>{1}</b>".format(url, item.original.name)
        },

    });

    tribute.attach(autocomplete);


}

function drag_and_drop() {

    $(".droppable").droppable(
        {
            accept: ".post",
            drop: function (event, ui) {

                // Source post being dragged.
                var source = ui.draggable;

                // Parent post to drop into.
                var parent = $(this).closest(".post");
                if (!parent.length) {
                    parent = $(this)
                }

                // Move target post to parent.
                move_post(parent, source);
            },

        });

    // Bind to any post object with the .draggable class
    $('.draggable').mousedown(function () {
        $(this).css('cursor', 'grabbing');
        var post = $(this).closest('.post');

        post.draggable(
            {
                addClasses: false,
                scroll: false,
                helper: 'clone',
                iframeFix: true,
                opacity: .7,
                containment: $('body'),
                revert: true,
                zIndex: 100,
                cursor: 'grabbing'

            });
    });


}
