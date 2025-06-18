import os
import pytest
from mcp_server.config import load_config, apply_cli_args, get_argument_parser
from werkzeug.security import generate_password_hash

def test_load_default_config(monkeypatch, tmp_path):
    # Ensure no actual config file is found, and no env vars are set that would override defaults
    monkeypatch.setattr(os, 'getenv', lambda k, d=None: d) # No env vars
    monkeypatch.setattr('mcp_server.config.DEFAULT_CONFIG_PATH', str(tmp_path / "non_existent_config.yaml"))

    config = load_config()

    assert config['server']['port'] == 5000 # Default port
    assert config['logging']['level'] == 'INFO'
    assert config['web_auth']['username'] == 'admin'

def test_load_from_yaml_file(test_config_path, monkeypatch):
    monkeypatch.setattr(os, 'getenv', lambda k, d=None: d) # No env vars
    config = load_config(test_config_path)

    assert config['server']['port'] == 5005 # From test_config.yaml
    assert config['logging']['level'] == 'DEBUG'
    assert config['tools']['script_runner']['scripts_base_path'] == 'tests/scripts'

def test_override_with_env_variables(test_config_path, monkeypatch):
    new_port = "5006"
    new_log_level = "WARNING"
    new_secret = "env_secret"

    monkeypatch.setattr(os, 'getenv', lambda k, d=None: {
        'MCP_SERVER_PORT': new_port,
        'MCP_LOG_LEVEL': new_log_level,
        'MCP_SECRET_KEY': new_secret
    }.get(k, d)) # Only override specific env vars

    config = load_config(test_config_path) # test_config.yaml is loaded first

    assert config['server']['port'] == int(new_port)
    assert config['logging']['level'] == new_log_level
    assert config['server']['secret_key'] == new_secret

def test_apply_cli_args(app_config): # app_config already has some base settings
    parser = get_argument_parser()

    # Test overriding port via CLI
    args_port = parser.parse_args(['--port', '5007'])
    config_after_port_cli = apply_cli_args(app_config.copy(), args_port)
    assert config_after_port_cli['server']['port'] == 5007

    # Test disabling web UI via CLI
    args_disable_ui = parser.parse_args(['--disable-web-ui'])
    config_after_disable_ui = apply_cli_args(app_config.copy(), args_disable_ui)
    assert config_after_disable_ui['server']['enable_web_ui'] is False

    # Test enabling web UI via CLI (should take precedence if already false)
    temp_config = app_config.copy()
    temp_config['server']['enable_web_ui'] = False
    args_enable_ui = parser.parse_args(['--enable-web-ui'])
    config_after_enable_ui = apply_cli_args(temp_config, args_enable_ui)
    assert config_after_enable_ui['server']['enable_web_ui'] is True

    # Test debug flag
    args_debug = parser.parse_args(['--debug'])
    config_after_debug = apply_cli_args(app_config.copy(), args_debug)
    assert config_after_debug['server']['debug'] is True

def test_password_hash_env_override(monkeypatch, tmp_path):
    test_hash = generate_password_hash("env_password")
    monkeypatch.setattr(os, 'getenv', lambda k, d=None: {
        'MCP_WEB_PASSWORD_HASH': test_hash
    }.get(k, d))
    # Use a non-existent default path to ensure only defaults + env are used
    monkeypatch.setattr('mcp_server.config.DEFAULT_CONFIG_PATH', str(tmp_path / "non_existent_config.yaml"))


    config = load_config()
    assert config['web_auth']['password_hash'] == test_hash
