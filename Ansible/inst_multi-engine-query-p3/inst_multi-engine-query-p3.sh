#/usr/bin/bash

# First parameter is optional and expected to be -v or -vv or -vvv

# Make sure we have the right number of args
check_args() {
    if [ "$1" != "" ]; then
        echo "Debug mode: $1"
    fi
}

# Check if the script is run as root or not. If not, script is exited with message
run_as_root() {
    if [ "$(id -u)" != "0" ]; then
        echo -e "This script must be run as root. Please run using sudo..."
        exit 1
    fi
}

check_args "$#" "$1"
run_as_root

echo "ansible-playbook $1 -i ./hosts-local.yml -u root inst_multi-engine-query-p3.yml"
ansible-playbook $1 -i hosts-local.yml -u root inst_multi-engine-query-p3.yml

# Rename the log file with a timestamp and change ownership to nexthink
NOW=$( date '+%Y%m%d.%H%M%S' )
BASE=$(basename "$0" .sh)
mv inst_multi-engine-query-p3.log $BASE.$NOW.log
chown nexthink:nexthink $BASE.$NOW.log
