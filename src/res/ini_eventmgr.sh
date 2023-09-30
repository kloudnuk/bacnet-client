#!/bin/bash

# Expected output would look like below:
# watched_filename,event_names

inipath=$1
iopath=$2

[[ ! -f "$iopath" ]] && touch "$iopath"

nohup $(inotifywait -e close_write \
    --timefmt '%a, %d %b %y %T %z' \
    --format '%T,%w,%e' \
    -m \
    -q \
    -o "$iopath" \
    "$inipath") &
