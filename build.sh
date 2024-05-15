#!/bin/bash

function unlock_keyring() {
    read -rsp "Password: " pass
    export $(echo -n "${pass}" | gnome-keyring-daemon --replace --unlock)
    unset pass
}

function update_version {
    config_file="pyproject.toml"
    section_name="tool.poetry"
    option_name="version"
    new_option_value="$1"

    if grep -q "^\[$section_name\]" "$config_file"; then
        echo current: $(awk 'BEGIN{FS="="} NR==3{print $1 $2}' "$config_file")
        sed -i -E "/^\[$section_name\]/,/^\[/ s/^($option_name[[:space:]]*=[[:space:]]*).*/\1\"$new_option_value\"/" "$config_file"
        echo new: $(awk 'BEGIN{FS="="} NR==3{print $1 $2}' "$config_file")
    else
        echo "Section $section_name not found in $config_file."
    fi
}

function build_dist {
    poetry shell

    # TODO - provide test coverage before version update and build.

    update_version "$1"

    unlock_keyring
    rm -r dist/*
    poetry update
    poetry install --sync
    poetry build -f wheel
    cp -r src/res/ dist/
}

if [ build_dist "$1" ]; then
    echo Bacnet Client build version "$1" complete with no errors.
fi

# Code sign the wheel
