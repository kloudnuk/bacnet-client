#!/bin/bash

set -e

function errecho() {
    printf "%s\n" "$*" 1>&2
}

function unlock_keyring() {
    read -rsp "Password: " pass
    export "$(echo -n "${pass}" | gnome-keyring-daemon --replace --unlock)"
    unset pass
}

function update_version {
    config_file="pyproject.toml"
    section_name="tool.poetry"
    option_name="version"
    new_option_value="$1"

    if grep -q "^\[$section_name\]" "$config_file"; then
        echo current: $(awk 'BEGIN{FS="="} NR==3{print $1 $2}' "$config_file")
        sed -i -E "/^\[$section_name\]/,/^\[/ s/^(${option_name}[[:space:]]*=[[:space:]]*).*/\1\"${new_option_value}\"/" "$config_file"
        echo new: $(awk 'BEGIN{FS="="} NR==3{print $1 $2}' "$config_file")
    else
        echo "Section $section_name not found in $config_file."
    fi
}

function build_dist {
    poetry shell

    # TODO - provide test coverage before version update and build.
    now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    package="bacnet-client-$1-$now.zip"

    update_version "$1"

    unlock_keyring
    [[ -d 'dist/res' ]] && rm -r dist/*
    poetry update
    poetry install --sync --without test
    poetry build -f wheel
    echo '' >'src/res/ini.events'
    echo '' >'src/res/object-graph.pkl'
    cp -r src/res/ dist/
    zip -r "$package" dist/

    aws s3 cp "$package" s3://nuksoftware

    # shellcheck disable=SC2181
    if [[ ${?} -ne 0 ]]; then
        errecho "ERROR: AWS reports put-object operation failed."
        return 1
    fi

    rm "$package"
}

build_dist "$1"

# Code sign the wheel
