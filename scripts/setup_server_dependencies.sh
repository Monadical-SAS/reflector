#!/bin/sh

pip install --upgrade pip

cwd=$(pwd)
last_component="${cwd##*/}"
if [ "$last_component" = "reflector" ]; then
    pip install -r server-requirements.txt
elif [ "$last_component" = "scripts" ]; then
    pip install -r ../server-requirements.txt
fi
