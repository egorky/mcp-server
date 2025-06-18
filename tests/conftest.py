import pytest
import os
from mcp_server.app import app as flask_app, main as flask_main, config as global_config, tool_manager as global_tool_manager
from mcp_server.config import load_config, apply_cli_args, get_argument_parser
from mcp_server.tool_manager import ToolManager
from werkzeug.security import generate_password_hash
import tempfile
import shutil

@pytest.fixture(scope='session')
def test_config_path():
    return os.path.abspath('tests/config/test_config.yaml')

@pytest.fixture(scope='session')
def app_config(test_config_path):
    # Load test config directly
    # Ensure password_hash is set for auth tests
    cfg = load_config(test_config_path)
    cfg['web_auth']['password_hash'] = generate_password_hash('testpass')

    # Override paths to be relative to test execution if necessary
    # For example, if scripts_base_path needs to be absolute based on CWD
    # cfg['tools']['script_runner']['scripts_base_path'] = os.path.abspath(cfg['tools']['script_runner']['scripts_base_path'])
    # cfg['logging']['file'] = os.path.abspath(cfg['logging']['file'])


    # Create a temporary log file for the test session if not an absolute path
    if not os.path.isabs(cfg['logging']['file']):
        # Use a global variable to store the temp_log_dir path so it can be accessed in the app fixture for cleanup
        global _temp_log_dir
        _temp_log_dir = tempfile.mkdtemp(prefix="mcp_test_logs_")
        cfg['logging']['file'] = os.path.join(_temp_log_dir, cfg['logging']['file'])


    # Apply any default CLI args if your app expects them (e.g. if parser has defaults)
    # parser = get_argument_parser()
    # args = parser.parse_args([]) # Minimal args
    # cfg = apply_cli_args(cfg, args)
    return cfg

@pytest.fixture(scope='session')
def app(app_config):
    """Session-wide test_app instance configured with test_config."""

    # Apply the test configuration to the global flask_app instance
    # This is a bit tricky as the app is typically configured in main()
    # We need to ensure our test_config is used by the app context

    flask_app.config['TESTING'] = True
    # flask_app.config.from_mapping(app_config['server']) # Not all server settings are Flask config
    flask_app.secret_key = app_config['server']['secret_key']

    # Make the full config available to the app if needed (e.g. via app.extensions or a custom setup)
    # For now, the global 'config' in mcp_server.app will be updated by tests that need it.
    # This is not ideal, main() should ideally create and return app.

    # To properly test the app as it runs via main(), we might need to restructure main()
    # or use a pattern where main() can accept a config object.
    # For now, we'll configure flask_app directly for testing client,
    # and individual modules will be tested with app_config.

    # Set the global config for tests that might import it from mcp_server.app
    # This is a workaround for global state.
    # A better approach would be dependency injection or app factories.
    # setattr(mcp_server.app, 'config', app_config)

    # The tool_manager also needs to be initialized with this config
    # setattr(mcp_server.app, 'tool_manager', ToolManager(global_config=app_config))

    # For testing with live server, it's better to let Flask-Testing handle setup
    # For now, just return the app instance for client fixture.
    # The actual global 'config' and 'tool_manager' in app.py will be set by individual tests or fixtures
    # that explicitly call parts of main() or setup functions with the test config.

    # Ensure log directory exists for the test log file
    log_file_path = app_config['logging']['file']
    log_dir = os.path.dirname(log_file_path)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)


    yield flask_app

    # Cleanup: Remove temporary log directory after tests
    # Access the global _temp_log_dir variable for cleanup
    if '_temp_log_dir' in globals() and os.path.exists(_temp_log_dir):
        shutil.rmtree(_temp_log_dir)


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()

# Fixture to initialize the app's global config and tool_manager with test settings
# This is crucial for integration tests that rely on the app's global state.
@pytest.fixture(scope='function') # Function scope to reset for each test
def initialized_app_for_test(app_config, monkeypatch):
    # Monkeypatch the global config and tool_manager in mcp_server.app
    # This way, when API endpoints are called, they use the test config.

    # Patch load_config to return our specific test config
    def mock_load_config(config_path=None):
        # Return a copy to avoid modification across tests if necessary
        return app_config.copy()

    monkeypatch.setattr('mcp_server.app.load_config', mock_load_config)

    # Re-initialize parts of main to set global config and tool_manager
    # This is still a bit of a workaround for global state.
    # Ideally, app setup would be more factory-like.

    # Simulate part of main() to set global config and tool_manager
    import mcp_server.app
    mcp_server.app.config = app_config
    mcp_server.app.tool_manager = ToolManager(global_config=app_config)

    # Ensure logging is also set up with test config
    # mcp_server.app.setup_logging(app_config.get('logging', {})) # This might cause issues if called multiple times

    # Ensure web routes are registered if UI is enabled
    if app_config['server'].get('enable_web_ui', True):
        if not hasattr(flask_app, '_web_routes_registered_for_test'): # Avoid multiple registrations
             mcp_server.app.register_web_routes(flask_app)
             flask_app._web_routes_registered_for_test = True

    return flask_app
