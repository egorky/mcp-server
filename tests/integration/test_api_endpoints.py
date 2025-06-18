import pytest
import json
from flask import url_for

def test_health_endpoint(client):
    response = client.get(url_for('health_check'))
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "healthy"

def test_list_tools_api(client, initialized_app_for_test): # initialized_app ensures tool_manager is set
    response = client.get(url_for('list_tools_api'))
    assert response.status_code == 200
    json_data = response.get_json()
    # Based on test_config.yaml and default plugins (script_runner, api_caller)
    assert "script_runner" in json_data
    assert "api_caller" in json_data
    assert json_data["script_runner"]["description"] is not None

def test_execute_script_runner_via_api_success(client, initialized_app_for_test):
    payload = {
        "script_name": "test_script.sh",
        "arguments": "API_USER"
    }
    response = client.post(url_for('execute_tool_api', tool_name='script_runner'), json=payload)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert "Hello from test_script.sh" in json_data["data"]["stdout"]
    assert "Argument: API_USER" in json_data["data"]["stdout"]

def test_execute_script_runner_via_api_script_fail(client, initialized_app_for_test):
    payload = {
        "script_name": "test_script.sh",
        "arguments": "error"
    }
    response = client.post(url_for('execute_tool_api', tool_name='script_runner'), json=payload)
    assert response.status_code == 200 # API call is fine, tool itself failed
    json_data = response.get_json()
    assert json_data["success"] is False
    assert "Test script error output" in json_data["error"]

def test_execute_tool_not_found_api(client, initialized_app_for_test):
    response = client.post(url_for('execute_tool_api', tool_name='nonexistenttool'), json={})
    assert response.status_code == 404 # Tool not found should be 404
    json_data = response.get_json()
    assert json_data["success"] is False
    assert "Tool 'nonexistenttool' not found" in json_data["error"]

def test_execute_tool_bad_request_not_json_api(client, initialized_app_for_test):
    response = client.post(url_for('execute_tool_api', tool_name='script_runner'), data="not json")
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False
    assert "payload must be JSON" in json_data["error"]

# Basic test for api_caller - requires httpserver fixture
def test_execute_api_caller_via_api(client, initialized_app_for_test, httpserver):
    httpserver.expect_request("/test_endpoint").respond_with_json({"message": "mock success"})

    payload = {
        "url": httpserver.url_for("/test_endpoint"),
        "method": "GET"
    }
    response = client.post(url_for('execute_tool_api', tool_name='api_caller'), json=payload)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["status_code"] == 200
    assert json_data["data"]["response"]["message"] == "mock success"
