import pytest
import os
from mcp_server.app import app as flask_app #, main as flask_main, config as global_config, tool_manager as global_tool_manager
from mcp_server.config import load_config #, apply_cli_args, get_argument_parser
from mcp_server.tool_manager import ToolManager
from werkzeug.security import generate_password_hash
import tempfile
import shutil
import mcp_server.app # To allow monkeypatching its globals

@pytest.fixture(scope='session')
def test_config_path():
    return os.path.abspath('tests/config/test_config.yaml')

@pytest.fixture(scope='session')
def app_config(test_config_path):
    cfg = load_config(test_config_path)
    cfg['web_auth']['password_hash'] = generate_password_hash('testpass')

    # Add a default test API token
    cfg['api_auth'] = cfg.get('api_auth', {}) # Ensure api_auth section exists
    cfg['api_auth']['static_token'] = 'test_api_token_12345'
    cfg['api_auth']['header_name'] = 'X-API-KEY' # Default for tests

    if not os.path.isabs(cfg['logging']['file']):
        temp_log_dir_val = tempfile.mkdtemp(prefix="mcp_test_logs_")
        cfg['logging']['file'] = os.path.join(temp_log_dir_val, cfg['logging']['file'])
        # Store temp_log_dir in cfg to access it in app fixture for cleanup
        cfg['_temp_log_dir'] = temp_log_dir_val
    return cfg

@pytest.fixture(scope='session')
def app(app_config):
    flask_app.config['TESTING'] = True
    flask_app.secret_key = app_config['server']['secret_key']

    log_file_path = app_config['logging']['file']
    log_dir = os.path.dirname(log_file_path)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Set the global config_obj in mcp_server.app for the test session
    # This helps if parts of the app directly import config_obj
    mcp_server.app.config_obj = app_config
    # Also setup logging once with this config
    mcp_server.app.setup_logging(app_config.get('logging', {}))


    yield flask_app

    # Cleanup: Remove temporary log directory after tests if it was created
    temp_log_dir_to_clean = app_config.get('_temp_log_dir')
    if temp_log_dir_to_clean and os.path.exists(temp_log_dir_to_clean):
        shutil.rmtree(temp_log_dir_to_clean)


@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def initialized_app_for_test(app, app_config, monkeypatch): # app fixture ensures flask_app is configured
    # The app's global config_obj should already be set by the 'app' fixture's session scope.
    # However, tool_manager might need re-initialization if its state changes or depends on function-scoped things.
    # For safety, we can re-assign here.

    # Ensure the global config_obj in the app module is the test one.
    monkeypatch.setattr(mcp_server.app, 'config_obj', app_config, raising=False)

    # Re-initialize tool_manager with the correct app_config for this test function
    current_tool_manager = ToolManager(global_config=app_config)
    monkeypatch.setattr(mcp_server.app, 'tool_manager', current_tool_manager, raising=False)

    # Register web routes if UI is enabled and not already done by app fixture
    # This logic can be tricky with session vs function scope.
    # Simplest is to ensure routes are registered if needed.
    if app_config['server'].get('enable_web_ui', True):
        # Check if routes are already registered to avoid issues with duplicate route errors in Flask
        # This check is a bit of a hack; ideally, app factory pattern avoids this.
        # A simple way: check if a known web UI route exists.
        if not flask_app.url_map.is_endpoint_available('dashboard'):
             mcp_server.app.register_web_routes(flask_app)

    return flask_app
