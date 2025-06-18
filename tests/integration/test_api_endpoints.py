import pytest
import json
from flask import url_for
import mcp_server.app # To allow monkeypatching config_obj

# Helper to get configured API key and header
def get_api_auth_details(app_config):
    token = app_config['api_auth']['static_token']
    header_name = app_config['api_auth']['header_name']
    headers = {}
    if header_name.lower() == 'authorization':
        headers[header_name] = f'Bearer {token}'
    else:
        headers[header_name] = token
    return headers, token, header_name


def test_health_endpoint(client): # No auth needed for health
    response = client.get(url_for('health_check'))
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "healthy"

def test_list_tools_api_success(client, initialized_app_for_test, app_config):
    auth_headers, _, _ = get_api_auth_details(app_config)
    response = client.get(url_for('list_tools_api'), headers=auth_headers)
    assert response.status_code == 200
    json_data = response.get_json()
    assert "script_runner" in json_data
    assert "api_caller" in json_data

def test_list_tools_api_no_token(client, initialized_app_for_test):
    response = client.get(url_for('list_tools_api'))
    assert response.status_code == 401 # Unauthorized

def test_list_tools_api_invalid_token(client, initialized_app_for_test, app_config):
    _, _, header_name = get_api_auth_details(app_config)
    invalid_headers = {header_name: "invalid_dummy_token"}
    response = client.get(url_for('list_tools_api'), headers=invalid_headers)
    assert response.status_code == 401

def test_list_tools_api_server_token_not_configured(client, initialized_app_for_test, app_config, monkeypatch):
    # Simulate server not having a token configured
    original_token = app_config['api_auth']['static_token']

    # Create a deep copy of app_config to modify for this test
    config_copy = json.loads(json.dumps(app_config)) # Simple deep copy for dicts
    config_copy['api_auth']['static_token'] = None # Temporarily remove token

    monkeypatch.setattr(mcp_server.app, 'config_obj', config_copy) # Update live config_obj

    # Use a valid header name but any token, as the server-side token is None
    header_name_to_use = config_copy['api_auth'].get('header_name', 'X-API-KEY')
    headers_for_request = {header_name_to_use: "any_token_value"}

    response = client.get(url_for('list_tools_api'), headers=headers_for_request)
    assert response.status_code == 401 # Should still be 401
    json_data = response.get_json()
    assert "API key configuration error on server" in json_data.get("description", "")

    # Restore original app_config to mcp_server.app.config_obj for subsequent tests
    monkeypatch.setattr(mcp_server.app, 'config_obj', app_config)


def test_execute_script_runner_via_api_success(client, initialized_app_for_test, app_config):
    auth_headers, _, _ = get_api_auth_details(app_config)
    payload = {
        "script_name": "test_script.sh",
        "arguments": "API_USER"
    }
    response = client.post(url_for('execute_tool_api', tool_name='script_runner'), json=payload, headers=auth_headers)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True

def test_execute_api_no_token(client, initialized_app_for_test):
    payload = {"script_name": "test_script.sh"}
    response = client.post(url_for('execute_tool_api', tool_name='script_runner'), json=payload)
    assert response.status_code == 401

def test_execute_api_invalid_token(client, initialized_app_for_test, app_config):
    _, _, header_name = get_api_auth_details(app_config)
    invalid_headers = {header_name: "invalid_dummy_token"}
    payload = {"script_name": "test_script.sh"}
    response = client.post(url_for('execute_tool_api', tool_name='script_runner'), json=payload, headers=invalid_headers)
    assert response.status_code == 401

# Test with Authorization: Bearer header
def test_list_tools_api_auth_bearer_header(client, initialized_app_for_test, app_config, monkeypatch):

    config_copy_bearer = json.loads(json.dumps(app_config))
    original_header_name = config_copy_bearer['api_auth']['header_name']
    config_copy_bearer['api_auth']['header_name'] = 'Authorization' # Change to use Bearer
    monkeypatch.setattr(mcp_server.app, 'config_obj', config_copy_bearer)

    # get_api_auth_details will now create Authorization: Bearer header based on modified config_copy_bearer
    auth_headers, _, _ = get_api_auth_details(config_copy_bearer)

    response = client.get(url_for('list_tools_api'), headers=auth_headers)
    assert response.status_code == 200
    json_data = response.get_json()
    assert "script_runner" in json_data

    # Test invalid Bearer token
    response_invalid = client.get(url_for('list_tools_api'), headers={'Authorization': 'Bearer invalid'})
    assert response_invalid.status_code == 401

    # Test malformed Bearer token
    response_malformed = client.get(url_for('list_tools_api'), headers={'Authorization': 'Bearerspacetoken'}) # No space
    assert response_malformed.status_code == 401

    # Restore original header name in the main app_config if it was changed, or ensure config_obj is restored
    monkeypatch.setattr(mcp_server.app, 'config_obj', app_config)


# Existing tests for tool execution logic (params, errors) can remain, just need to pass auth headers.
def test_execute_script_runner_via_api_script_fail(client, initialized_app_for_test, app_config):
    auth_headers, _, _ = get_api_auth_details(app_config)
    payload = {"script_name": "test_script.sh", "arguments": "error"}
    response = client.post(url_for('execute_tool_api', tool_name='script_runner'), json=payload, headers=auth_headers)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is False

def test_execute_tool_not_found_api(client, initialized_app_for_test, app_config):
    auth_headers, _, _ = get_api_auth_details(app_config)
    response = client.post(url_for('execute_tool_api', tool_name='nonexistenttool'), json={}, headers=auth_headers)
    assert response.status_code == 404

def test_execute_tool_bad_request_not_json_api(client, initialized_app_for_test, app_config):
    auth_headers, _, _ = get_api_auth_details(app_config)
    response = client.post(url_for('execute_tool_api', tool_name='script_runner'), data="not json", headers=auth_headers)
    assert response.status_code == 400

def test_execute_api_caller_via_api(client, initialized_app_for_test, app_config, httpserver):
    auth_headers, _, _ = get_api_auth_details(app_config)
    httpserver.expect_request("/test_endpoint").respond_with_json({"message": "mock success"})
    payload = {"url": httpserver.url_for("/test_endpoint"), "method": "GET"}
    response = client.post(url_for('execute_tool_api', tool_name='api_caller'), json=payload, headers=auth_headers)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
