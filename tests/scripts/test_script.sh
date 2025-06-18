#!/bin/bash
echo "Hello from test_script.sh"
if [ "$1" == "error" ]; then
  >&2 echo "Test script error output"
  # The script_runner tool itself will check the exit code.
  # For the purpose of creating the file, we don't need 'exit 1' here.
  # The test will assert the behavior based on the tool's interpretation of the script's execution.
fi
echo "Argument: $1"
# The script_runner tool itself will check the exit code.
