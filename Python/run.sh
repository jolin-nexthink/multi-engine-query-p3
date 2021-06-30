#!/bin/bash

########################################################
# Runs Python utility to perfroma an NXQL query across #
# all detected engines                                 #
#                                                      #
# Last review : Apr. 15, 2020                          #
# Authors : J. Olin (Nexthink)                         #
########################################################

# Go the project directory
cd /home/nexthink

# Set virtualenv environment settings
source .bashrc >/dev/null 2>%1

# Go the correct directory
cd /home/nexthink/custom/multi-engine-query-p3

# Activate the virtual environment
source activate multi-engine-query-p3 >/dev/null 2>&1

# Remove any existing .log and .out files older than 7 days
find ./output/logs \( -type f -a \( -iname '*.log' -o -iname '*.out' \) -a -mtime +6 \) -delete

# Run the script
python3 multi-engine-query-p3.py $1 $2 $3 $4 $5 $6 $7 $8 $9

# Deactivate the virtual environment
source deactivate
