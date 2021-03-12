#!/bin/bash

set -ue

# Ho
HOW_OFTEN='--hourly'

# Load the conda commands.
source ~/miniconda3/etc/profile.d/conda.sh

export POSTGRES_HOST=/var/run/postgresql

# Activate the conda environemnt.
conda activate engine

# Set the configuration module.
export DJANGO_SETTINGS_MODULE=conf.run.site_settings


python manage.py digest ${HOW_OFTEN}