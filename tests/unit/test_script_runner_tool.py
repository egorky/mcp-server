import pytest
from mcp_server.tools.plugins.script_runner import ScriptRunnerTool
import os
import time

@pytest.fixture
def script_runner_cfg(app_config):
    # app_config already has tools.script_runner.scripts_base_path = tests/scripts
    # and tools.script_runner.default_timeout = 5
    tool_cfg = app_config.get('tools', {}).get('script_runner', {})
    return tool_cfg

@pytest.fixture
def script_runner(script_runner_cfg):
    return ScriptRunnerTool(config=script_runner_cfg)


def test_script_runner_success(script_runner):
    params = {"script_name": "test_script.sh", "arguments": "TestArg"}
    result = script_runner.execute(params)
    assert result["success"] is True
    assert "Hello from test_script.sh" in result["data"]["stdout"]
    assert "Argument: TestArg" in result["data"]["stdout"]

def test_script_runner_failure_exit_code(script_runner):
    params = {"script_name": "test_script.sh", "arguments": "error"}
    result = script_runner.execute(params)
    assert result["success"] is False
    assert "Test script error output" in result["error"]

def test_script_runner_script_not_found(script_runner):
    params = {"script_name": "non_existent_script.sh"}
    result = script_runner.execute(params)
    assert result["success"] is False
    assert "Script file not found" in result["error"]

def test_script_runner_default_timeout_from_config(script_runner, script_runner_cfg):
    # timeout_script.sh sleeps for 10s. Default config timeout is 5s.
    params = {"script_name": "timeout_script.sh"}

    start_time = time.time()
    result = script_runner.execute(params)
    duration = time.time() - start_time

    assert result["success"] is False
    assert "Script execution timed out" in result["error"]
    # Check if it respected the configured default_timeout (5s)
    assert duration < 7 # Allow some buffer, should be around 5s

def test_script_runner_per_execution_timeout_override_shorter(script_runner):
    # timeout_script.sh sleeps for 10s. Per-execution timeout set to 1s.
    params = {"script_name": "timeout_script.sh", "timeout": 1} # Override default 5s with 1s

    start_time = time.time()
    result = script_runner.execute(params)
    duration = time.time() - start_time

    assert result["success"] is False
    assert "Script execution timed out" in result["error"]
    assert duration < 3 # Should be around 1s

def test_script_runner_per_execution_timeout_override_longer_success(script_runner):
    # test_script.sh is quick. Set a longer per-execution timeout than default.
    # Default is 5s. Set per-exec to 8s.
    params = {"script_name": "test_script.sh", "arguments": "LongerTimeout", "timeout": 8}
    result = script_runner.execute(params)
    assert result["success"] is True
    assert "Argument: LongerTimeout" in result["data"]["stdout"]

def test_script_runner_invalid_per_execution_timeout_uses_default(script_runner, script_runner_cfg, caplog):
    # timeout_script.sh sleeps 10s. Config default timeout is 5s.
    # Pass invalid per-execution timeout. Should fall back to 5s.
    params = {"script_name": "timeout_script.sh", "timeout": "not-an-int"}

    start_time = time.time()
    result = script_runner.execute(params)
    duration = time.time() - start_time

    assert result["success"] is False
    assert "Script execution timed out" in result["error"]
    assert duration < 7 # Should be around 5s (default)
    assert "Invalid 'timeout' parameter for script 'timeout_script.sh'" in caplog.text


def test_script_runner_not_executable(script_runner, tmp_path):
    base_path = script_runner.config.get("scripts_base_path", "tests/scripts")
    # Ensure base_path is absolute for creating the test file reliably
    if not os.path.isabs(base_path):
        # This assumes tests are run from project root, so tests/scripts is correct relative path.
        # For more robustness, one might use pytest's tmp_path_factory or ensure app_config makes it absolute.
        # For this test, we'll assume 'tests/scripts' can be resolved from current working dir.
        # However, the fixture `app_config` should ideally make this absolute.
        # Let's assume it is for now.
        pass

    # Create the non_exec.sh inside the designated scripts_base_path
    # This means it needs to be tests/scripts/non_exec.sh
    # The tmp_path fixture gives a temporary directory *outside* the project structure.
    # We need to place this file within the path the tool is configured to look at.

    # Construct path within the configured scripts_base_path
    # Ensure scripts_base_path exists for the test
    if not os.path.exists(base_path):
        os.makedirs(base_path)

    non_exec_script_name = "non_exec_test.sh"
    non_exec_script_full_path = os.path.join(base_path, non_exec_script_name)

    with open(non_exec_script_full_path, "w") as f:
        f.write("#!/bin/bash\necho 'should not run'")
    os.chmod(non_exec_script_full_path, 0o644)

    params = {"script_name": non_exec_script_name}
    result = script_runner.execute(params)

    assert result["success"] is False
    assert "Script file is not executable" in result["error"]

    # Clean up the created script
    os.remove(non_exec_script_full_path)
