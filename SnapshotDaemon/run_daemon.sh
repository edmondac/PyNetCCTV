#!/bin/bash

if ! test -e daemon.conf
then
    echo "Please create a daemon.conf file (from daemon.conf.in)"
    exit 1
fi

#Get DJANGOPROJECT* from config file
grep DJANGOPROJECT daemon.conf > .config.tmp
source .config.tmp

export PYTHONPATH=$PYTHONPATH:$DJANGOPROJECT_PARENT_PATH:$DJANGOPROJECT_PARENT_PATH/$DJANGOPROJECT
export DJANGO_SETTINGS_MODULE=$DJANGOPROJECT.settings

python Snapshot.py $@ &

echo "Launched"