import pytest
from mcp_server.tools.plugins.script_runner import ScriptRunnerTool
import os

@pytest.fixture
def script_runner(app_config): # app_config has tools.script_runner.scripts_base_path
    # Get the tool-specific config for script_runner
    tool_cfg = app_config.get('tools', {}).get('script_runner', {})
    return ScriptRunnerTool(config=tool_cfg)

def test_script_runner_success(script_runner):
    # scripts_base_path is 'tests/scripts' from app_config -> test_config.yaml
    params = {"script_name": "test_script.sh", "arguments": "TestArg"}
    result = script_runner.execute(params)

    assert result["success"] is True
    assert "Hello from test_script.sh" in result["data"]["stdout"]
    assert "Argument: TestArg" in result["data"]["stdout"]
    assert result["data"]["return_code"] == 0

def test_script_runner_failure_exit_code(script_runner):
    params = {"script_name": "test_script.sh", "arguments": "error"}
    result = script_runner.execute(params)

    assert result["success"] is False
    assert "Test script error output" in result["error"] # Stderr goes to error field on failure
    assert result["data"]["return_code"] == 1

def test_script_runner_script_not_found(script_runner):
    params = {"script_name": "non_existent_script.sh"}
    result = script_runner.execute(params)

    assert result["success"] is False
    assert "Script file not found" in result["error"]

def test_script_runner_timeout(script_runner, app_config):
    # Timeout is 5s in test_config.yaml for script_runner
    # timeout_script.sh sleeps for 10s
    # Note: This test actually waits for the timeout.
    params = {"script_name": "timeout_script.sh"}
    result = script_runner.execute(params)

    assert result["success"] is False
    assert "Script execution timed out" in result["error"]

def test_script_runner_not_executable(script_runner, tmp_path):
    # Create a non-executable script within the configured scripts_base_path
    # This requires knowing the scripts_base_path from the fixture's config.
    base_path = script_runner.config.get("scripts_base_path", "tests/scripts")
    if not os.path.isabs(base_path): # Ensure it's usable
        base_path = os.path.abspath(base_path)

    non_exec_script_path = os.path.join(base_path, "non_exec.sh")
    with open(non_exec_script_path, "w") as f:
        f.write("#!/bin/bash\necho 'should not run'")
    # Ensure it's NOT executable (default perms might be, so explicitly set)
    os.chmod(non_exec_script_path, 0o644)

    params = {"script_name": "non_exec.sh"}
    result = script_runner.execute(params)

    assert result["success"] is False
    assert "Script file is not executable" in result["error"]

    # Clean up
    os.remove(non_exec_script_path)
