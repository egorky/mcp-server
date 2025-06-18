#!/bin/bash
echo "Timeout script started"
sleep 10 # This should exceed the 5s timeout in test_config.yaml
echo "Timeout script finished (should not happen)"
# The script_runner tool itself will check the exit code.
