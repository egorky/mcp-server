import logging
import logging.handlers # For RotatingFileHandler
import os
from flask import (
    Flask, jsonify, request, render_template,
    session, redirect, url_for, flash, abort
)
from werkzeug.security import check_password_hash # generate_password_hash removed as it's in utils
from functools import wraps

from mcp_server.config import load_config, get_argument_parser, apply_cli_args
from mcp_server.tool_manager import ToolManager

# Initialize a basic logger for early messages (before full setup)
# This basicConfig will be overridden by setup_logging if successful.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - PRECONFIG - %(message)s')
logger = logging.getLogger(__name__) # This will be the app's main logger

def setup_logging(log_config):
    """Configures logging based on the loaded configuration."""
    log_level_str = log_config.get('level', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    log_file = log_config.get('file')
    log_format_str = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    max_bytes = int(log_config.get('max_bytes', 1024*1024*5)) # Default 5MB
    backup_count = int(log_config.get('backup_count', 3)) # Default 3 backups

    # Get root logger to configure all loggers in the application
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers to prevent duplicate logging
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close() # Close handler before removing

    log_formatter = logging.Formatter(log_format_str)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(log_level) # Set level for handler too
    root_logger.addHandler(console_handler)

    if log_file:
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                root_logger.info(f"Created log directory: {log_dir}")

            # Rotating File Handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
            )
            file_handler.setFormatter(log_formatter)
            file_handler.setLevel(log_level) # Set level for handler too
            root_logger.addHandler(file_handler)
            root_logger.info(f"Logging to file: {log_file} (Level: {log_level_str}, Rotation: {max_bytes}b, {backup_count} backups)")
        except Exception as e:
            root_logger.error(f"Failed to set up file logging to {log_file}: {e}", exc_info=True)
    else:
        root_logger.info(f"File logging is disabled. Logging to console only (Level: {log_level_str}).")

    # After setup, use the app's named logger for its messages
    logger.info(f"Logging system configured. Effective log level for '{logger.name}': {logging.getLevelName(logger.getEffectiveLevel())}")


app = Flask(__name__)
# Configure Flask's internal logger to use our handlers if desired, or disable it to prevent duplicate request logs.
# By default, Flask logs to stderr. If we want it in our file log, we can propagate.
# app.logger is a standard Python logger. Its propagation is True by default.
# Werkzeug logger (used by Flask dev server for requests) is 'werkzeug'.
werkzeug_logger = logging.getLogger('werkzeug')
# If we want to control werkzeug logs (request logs from dev server):
# werkzeug_logger.setLevel(logging.INFO) # Or whatever level
# For now, let setup_logging configure the root logger, which werkzeug will inherit if not specifically configured.

app.secret_key = os.urandom(24)

config = None
tool_manager = None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access this page.', 'warning')
            logger.warning(f"Unauthorized access attempt to '{f.__name__}' from IP {request.remote_addr}. Redirecting to login.")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/health', methods=['GET'])
def health_check():
    logger.info(f"Health check request from {request.remote_addr}.")
    return jsonify({"status": "healthy", "message": "MCP Server is running."}), 200

@app.route('/tools', methods=['GET'])
def list_tools_api():
    if not tool_manager:
        logger.error("Tool manager not available during /tools API request.")
        return jsonify({"error": "Tool manager not available"}), 500
    tools_data = tool_manager.get_all_tools()
    logger.info(f"API /tools requested by {request.remote_addr}. Responding with {len(tools_data)} tools.")
    return jsonify(tools_data), 200

@app.route('/tools/<string:tool_name>/execute', methods=['POST'])
def execute_tool_api(tool_name):
    if not tool_manager:
        logger.error(f"Tool manager not available for /tools/{tool_name}/execute API request.")
        return jsonify({"error": "Tool manager not available"}), 500

    logger.info(f"API /tools/{tool_name}/execute requested by {request.remote_addr}.")
    tool = tool_manager.get_tool(tool_name)
    if not tool:
        logger.warning(f"API: Attempt to execute non-existent tool '{tool_name}' by {request.remote_addr}.")
        return jsonify({"success": False, "error": f"Tool '{tool_name}' not found."}), 404

    if not request.is_json:
        logger.warning(f"API: Invalid request to execute {tool_name} (not JSON) by {request.remote_addr}.")
        return jsonify({"success": False, "error": "Invalid request: payload must be JSON."}), 400

    params = request.get_json()
    # Be cautious about logging raw params if they contain sensitive data.
    # Consider logging only keys or a summary. For now, logging as is for debug.
    logger.debug(f"API: Executing tool '{tool_name}' with params: {params} (requested by {request.remote_addr})")

    try:
        result = tool_manager.execute_tool(tool_name, params)
        if result.get("success"):
            logger.info(f"API: Tool '{tool_name}' executed successfully by {request.remote_addr}.")
        else:
            logger.warning(f"API: Tool '{tool_name}' execution failed for {request.remote_addr}. Error: {result.get('error')}")
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"API: Unexpected error executing tool {tool_name} for {request.remote_addr}: {e}", exc_info=True)
        return jsonify({"success": False, "error": "An unexpected server error occurred."}), 500

def register_web_routes(app_instance):
    logger.info("Registering Web UI routes.")

    @app_instance.route('/')
    @login_required
    def index_redirect():
        return redirect(url_for('dashboard'))

    @app_instance.route('/dashboard')
    @login_required
    def dashboard():
        logger.debug(f"Dashboard accessed by user '{session.get('username')}' from {request.remote_addr}.")
        return render_template('dashboard.html')

    @app_instance.route('/login', methods=['GET', 'POST'])
    def login():
        if session.get('logged_in'):
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            username_form = request.form.get('username')
            password_form = request.form.get('password') # Do not log password_form

            cfg_username = config.get('web_auth', {}).get('username')
            hashed_password = config.get('web_auth', {}).get('password_hash')

            if not cfg_username or not hashed_password:
                flash('Web authentication is not properly configured on the server.', 'danger')
                logger.error(f"Login attempt from {request.remote_addr} failed: Web auth not configured.")
                return render_template('login.html')

            if username_form == cfg_username and check_password_hash(hashed_password, password_form):
                session['logged_in'] = True
                session['username'] = username_form
                logger.info(f"User '{username_form}' logged in successfully from {request.remote_addr}.")
                flash('Login successful!', 'success')
                next_url = request.args.get('next')
                return redirect(next_url or url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'danger')
                logger.warning(f"Failed login attempt for user '{username_form}' from {request.remote_addr}.")

        return render_template('login.html')

    @app_instance.route('/logout')
    @login_required
    def logout():
        user = session.get('username', 'unknown')
        logger.info(f"User '{user}' logging out from {request.remote_addr}.")
        session.pop('logged_in', None)
        session.pop('username', None)
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))

def main():
    global config, tool_manager, app

    # Initial logging before full config is loaded
    logger.info("MCP Server starting up...")

    arg_parser = get_argument_parser()
    args = arg_parser.parse_args()

    # Load configuration - this might log using basicConfig if path is wrong
    loaded_main_config = load_config(args.config) # Renamed to avoid conflict with global 'config'

    # Apply CLI arguments to override loaded config
    final_config = apply_cli_args(loaded_main_config, args) # Renamed

    # Assign to global config *after* all overrides
    config = final_config

    # Setup logging based on the final configuration
    # This will reconfigure the root logger and its handlers.
    setup_logging(config.get('logging', {}))

    logger.info(f"Final configuration loaded. Debug mode: {config['server']['debug']}")

    app.secret_key = config.get('server', {}).get('secret_key', app.secret_key)
    if app.secret_key == os.urandom(24) and config['server'].get('enable_web_ui', True): # Check if it's still the default
         logger.warning("Using a default random Flask secret_key. Set a permanent 'secret_key' in config for production if Web UI is enabled.")

    tool_manager = ToolManager(global_config=config) # ToolManager also logs using the configured system

    logger.info(f"Available tools: {list(tool_manager.get_all_tools().keys())}")

    if config['server'].get('enable_web_ui', True):
        if not config.get('web_auth', {}).get('username') or not config.get('web_auth', {}).get('password_hash'):
            logger.error("Web UI is enabled, but 'web_auth.username' or 'web_auth.password_hash' is missing. Web login will fail.")
        register_web_routes(app)
        # logger.info("Web UI is ENABLED.") # Already logged in register_web_routes
    else:
        logger.info("Web UI is DISABLED by configuration.")
        # Simplified disabled UI handling: if routes are not registered, they 404.
        # The catch-all can be removed if this behavior is acceptable.
        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
        def catch_all_disabled_ui(path):
            logger.info(f"Web UI is disabled. Request to '{path}' from {request.remote_addr} resulted in 404.")
            abort(404, description="Web interface is disabled.")


    logger.info(f"MCP Server starting on {config['server']['host']}:{config['server']['port']}. Web UI enabled: {config['server']['enable_web_ui']}.")

    # Note: app.run() is for development. For production, use a WSGI server like Gunicorn.
    # When using Gunicorn, its own access/error logs will also be generated.
    app.run(
        host=config['server']['host'],
        port=config['server']['port'],
        debug=config['server']['debug']
    )
    logger.info("MCP Server shutting down.") # This line might not be reached if app.run() blocks or server is killed

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # Catch-all for critical startup errors before or outside Flask's error handling
        logger.critical(f"Critical error during server startup or main execution: {e}", exc_info=True)
        # Depending on where this happens, file logging might not be set up.
        # BasicConfig should catch it on console.
        # If using systemd, this might also go to journald.
        raise # Re-raise the exception after logging
