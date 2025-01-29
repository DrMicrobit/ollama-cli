#!/bin/sh

# This will simply run pre-commit with the commit-msg hook
# The configiration for this is in the file: .pre-commit-config.yaml

pre-commit install -t commit-msg
echo "Done, your commit summary lines will now be checked."
