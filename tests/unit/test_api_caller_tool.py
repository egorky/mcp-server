import pytest
from mcp_server.tools.plugins.api_caller import ApiCallerTool
from unittest.mock import patch, MagicMock
import requests # For exceptions

@pytest.fixture
def api_caller_tool_default_config():
    # Config matching new defaults in api_caller.py if no config is passed
    return ApiCallerTool(config={
        "default_connect_timeout": 7, # Different from internal tool default for testing
        "default_read_timeout": 17  # Different from internal tool default for testing
    })

@pytest.fixture
def api_caller_tool_old_default_config():
    return ApiCallerTool(config={"default_timeout": 25})


@patch('requests.request')
def test_api_caller_separate_timeouts_from_params(mock_request, api_caller_tool_default_config):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "success"}
    mock_response.headers = {}
    mock_request.return_value = mock_response

    params = {"url": "http://example.com", "method": "GET", "connect_timeout": 5, "read_timeout": 15}
    api_caller_tool_default_config.execute(params)

    mock_request.assert_called_once()
    args, kwargs = mock_request.call_args
    assert kwargs['timeout'] == (5.0, 15.0) # requests lib uses float

@patch('requests.request')
def test_api_caller_overall_timeout_from_params(mock_request, api_caller_tool_default_config):
    mock_response = MagicMock() # ...
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "success"}
    mock_response.headers = {}
    mock_request.return_value = mock_response
    params = {"url": "http://example.com", "method": "GET", "timeout": 20}
    api_caller_tool_default_config.execute(params)
    args, kwargs = mock_request.call_args
    assert kwargs['timeout'] == 20.0 # requests lib uses float

@patch('requests.request')
def test_api_caller_tool_config_separate_timeouts(mock_request, api_caller_tool_default_config):
    mock_response = MagicMock() # ...
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "success"}
    mock_response.headers = {}
    mock_request.return_value = mock_response
    # Uses default_connect_timeout: 7, default_read_timeout: 17 from fixture
    params = {"url": "http://example.com", "method": "GET"}
    api_caller_tool_default_config.execute(params)
    args, kwargs = mock_request.call_args
    assert kwargs['timeout'] == (7.0, 17.0) # requests lib uses float

@patch('requests.request')
def test_api_caller_tool_config_old_overall_timeout(mock_request, api_caller_tool_old_default_config):
    mock_response = MagicMock() # ...
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "success"}
    mock_response.headers = {}
    mock_request.return_value = mock_response
    # Uses default_timeout: 25 from fixture
    params = {"url": "http://example.com", "method": "GET"}
    api_caller_tool_old_default_config.execute(params)
    args, kwargs = mock_request.call_args
    assert kwargs['timeout'] == 25.0

@patch('requests.request')
def test_api_caller_param_overall_overrides_tool_separate(mock_request, api_caller_tool_default_config):
    mock_response = MagicMock() # ...
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "success"}
    mock_response.headers = {}
    mock_request.return_value = mock_response
    # Tool default is (7,17), param is 22 overall
    params = {"url": "http://example.com", "method": "GET", "timeout": 22}
    api_caller_tool_default_config.execute(params)
    args, kwargs = mock_request.call_args
    assert kwargs['timeout'] == 22.0 # Overall param should win if specific not given

@patch('requests.request')
def test_api_caller_param_specific_overrides_tool_overall(mock_request, api_caller_tool_old_default_config):
    mock_response = MagicMock() # ...
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "success"}
    mock_response.headers = {}
    mock_request.return_value = mock_response
    # Tool default is 25 overall, params are (6, 16) specific
    params = {"url": "http://example.com", "method": "GET", "connect_timeout": 6, "read_timeout": 16}
    api_caller_tool_old_default_config.execute(params)
    args, kwargs = mock_request.call_args
    assert kwargs['timeout'] == (6.0, 16.0) # Specific params win

@patch('requests.request')
def test_api_caller_connect_timeout_exception(mock_request, api_caller_tool_default_config):
    mock_request.side_effect = requests.exceptions.ConnectTimeout("Connection timed out")
    params = {"url": "http://example.com", "method": "GET", "connect_timeout": 0.1, "read_timeout": 0.1}
    result = api_caller_tool_default_config.execute(params)
    assert result["success"] is False
    assert "connection timed out" in result["error"].lower()

@patch('requests.request')
def test_api_caller_read_timeout_exception(mock_request, api_caller_tool_default_config):
    mock_request.side_effect = requests.exceptions.ReadTimeout("Read timed out")
    params = {"url": "http://example.com", "method": "GET", "connect_timeout": 1, "read_timeout": 0.1}
    result = api_caller_tool_default_config.execute(params)
    assert result["success"] is False
    assert "read timed out" in result["error"].lower()

# Test for when no timeouts are configured at all (should use internal tool defaults)
@patch('requests.request')
def test_api_caller_no_timeouts_configured(mock_request):
    tool_no_timeout_config = ApiCallerTool(config={}) # Empty tool config
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "success"}
    mock_response.headers = {}
    mock_request.return_value = mock_response
    params = {"url": "http://example.com", "method": "GET"}
    tool_no_timeout_config.execute(params)
    args, kwargs = mock_request.call_args
    # Should fall back to the hardcoded defaults in _determine_timeout() if all configs/params are missing
    assert kwargs['timeout'] == (10.0, 30.0) # (default_connect_timeout, default_read_timeout) from the tool's code
