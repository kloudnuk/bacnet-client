# This script will create a inotifywait and feed its output to the python app using a coproc command with pipes.
# There is a chance the inotifywait will need to be in a separate script for the coproc command to work properly, in any case resmgr will be the coprocessor and pipe event
#   notifications from inotifywait to the python app, so the app can cancel service tasks and issue on demamnd read_setting calls to update configuration values used
#   during runtime.
