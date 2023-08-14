#!/bin/bash

source build/ado.env

function unlock_keyring() {
    export "$(echo -n "${pass}" | gnome-keyring-daemon --replace --unlock)"
    unset "${pass}"
}

# apt update | apt upgrade -y

if apt list --installed | grep -q software-properties-common; then
    echo '...software-properties-common found'
else
    apt install software-properties-common -y
fi

if apt list --installed | grep -q pipx; then
    echo '...pipx found'
else
    apt install pipx -y
fi

if apt list --installed | grep -q python3.10; then
    echo '...python3.10 found'
else
    apt install python3.10 -y
fi

if pipx list | grep -q poetry; then
    echo '...poetry found'
else
    pipx install poetry==1.4.2
fi

# if pip list | grep -q shiv; then
#     echo '...shiv found'
# else
#     pip install shiv
# fi

# if apt list --installed | grep -q libsecret-tools; then
#     echo '...libsecret-tools found'
# else
#     apt install libsecret-tools -y
# fi

find src/res -type f -print0 |
    tar czvf dist/res.tar.gz --null -T -

poetry install --without test --sync
poetry build -f wheel

echo "$ado_bacnetclient_pat" | az devops login --organization https://dev.azure.com/vtsmolinski/

az artifacts universal publish \
    --organization https://dev.azure.com/vtsmolinski/ \
    --project="DataBot" \
    --scope project \
    --feed databot \
    --name bacnet-client \
    --version 0.0.4 \
    --description "a bacnet-ip client to discover devices and their data to sample in real-time and collect time series on a cloud service." \
    --path dist

az devops logout --organization https://dev.azure.com/vtsmolinski/

# TODO - Sign artifacts with a code signing certificate.
# TODO - Add code to the downstream to cut a account-specific mongodb mTLS certificate an add it to the res folder.
