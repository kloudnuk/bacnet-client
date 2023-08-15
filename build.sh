#!/bin/bash

#   find src/res -type f -print0 |
#       tar czvf dist/res.tar.gz --null -T -

cp -r res ../dist/res

poetry install

read -ra site_packs <<<"$(poetry run python3.10 -c 'import site; print(site.getsitepackages())')"
site_path="${site_packs[0]/\[\'/}"
site_path="${site_path/\',/}"
echo "$site_path"

interpreter=$(which python3.10)
echo "$interpreter"

shiv -p "$interpreter" -e bacnet_client.app:main --site-packages "$site_path" -o ../dist/bacnet_client.pyz

# chmod +x dist/bacnet_client.pyz

poetry run python3.10 ../dist/bacnet_client.pyz
