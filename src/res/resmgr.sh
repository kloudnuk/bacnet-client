#!/bin/bash

# This script will create a inotifywait and feed its output to the python app using a coproc command with pipes.
# There is a chance the inotifywait will need to be in a separate script for the coproc command to work properly, in any case resmgr will be the coprocessor and pipe event
#   notifications from inotifywait to the python app, so the app can cancel service tasks and issue on demamnd read_setting calls to update configuration values used
#   during runtime.

# Expected output would look like below:
# watched_filename,event_names

function run {
    inotifywait -e modify \
        --timefmt '%a, %d %b %y %T %z' \
        --format '%T,%w,%e' \
        -m $1
}

run $1
