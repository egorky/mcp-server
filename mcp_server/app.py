import logging
import logging.handlers
import os
from flask import (
    Flask, jsonify, request, render_template,
    session, redirect, url_for, flash, abort
)
from werkzeug.security import check_password_hash
from functools import wraps

from mcp_server.config import load_config, get_argument_parser, apply_cli_args
from mcp_server.tool_manager import ToolManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - PRECONFIG - %(message)s')
logger = logging.getLogger(__name__)

def setup_logging(log_config):
    log_level_str = log_config.get('level', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    log_file = log_config.get('file')
    log_format_str = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    max_bytes = int(log_config.get('max_bytes', 1024*1024*5))
    backup_count = int(log_config.get('backup_count', 3))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    log_formatter = logging.Formatter(log_format_str)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    if log_file:
        try:
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                root_logger.info(f"Created log directory: {log_dir}")
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
            )
            file_handler.setFormatter(log_formatter)
            file_handler.setLevel(log_level)
            root_logger.addHandler(file_handler)
            root_logger.info(f"Logging to file: {log_file} (Level: {log_level_str}, Rotation: {max_bytes}b, {backup_count} backups)")
        except Exception as e:
            root_logger.error(f"Failed to set up file logging to {log_file}: {e}", exc_info=True)
    else:
        root_logger.info(f"File logging is disabled. Logging to console only (Level: {log_level_str}).")
    logger.info(f"Logging system configured. Effective log level for '{logger.name}': {logging.getLevelName(logger.getEffectiveLevel())}")

app = Flask(__name__)
app.secret_key = os.urandom(24)

config_obj = None # Renamed to avoid conflict with flask.config
tool_manager = None

# === Authentication Decorators ===
def login_required(f): # For Web UI
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access this page.', 'warning')
            logger.warning(f"Unauthorized Web UI access attempt to '{f.__name__}' from IP {request.remote_addr}. Redirecting to login.")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def api_key_required(f): # For API
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_token = None
        # Use config_obj here
        configured_token = config_obj.get('api_auth', {}).get('static_token')
        header_name = config_obj.get('api_auth', {}).get('header_name', 'X-API-KEY')

        if not configured_token:
            logger.error(f"API authentication error: No static_token configured on the server for endpoint '{f.__name__}'. Denying access from {request.remote_addr}.")
            # For security, don't reveal that token is not configured to client. Just treat as unauthorized.
            abort(401, description="Access unauthorized. API key configuration error on server.")
            # Or, if you want to allow access if no token is configured (less secure):
            # logger.warning(f"API access allowed to '{f.__name__}' without token: No static_token configured.")
            # return f(*args, **kwargs)


        if header_name.lower() == 'authorization':
            auth_header = request.headers.get(header_name)
            if auth_header and auth_header.startswith('Bearer '):
                provided_token = auth_header.split(' ', 1)[1]
        else:
            provided_token = request.headers.get(header_name)

        if not provided_token:
            logger.warning(f"Unauthorized API access attempt to '{f.__name__}' from {request.remote_addr}: Missing API token in header '{header_name}'.")
            abort(401, description=f"Unauthorized. API token required in '{header_name}' header.")

        # Constant time comparison for tokens would be better for security, but for typical token lengths, direct comparison is common.
        # For very high security, use something like hmac.compare_digest.
        if provided_token == configured_token:
            return f(*args, **kwargs)
        else:
            logger.warning(f"Unauthorized API access attempt to '{f.__name__}' from {request.remote_addr}: Invalid API token.")
            abort(401, description="Unauthorized. Invalid API token.")
    return decorated_function

# === API Endpoints ===
@app.route('/health', methods=['GET'])
def health_check():
    logger.info(f"Health check request from {request.remote_addr}.")
    return jsonify({"status": "healthy", "message": "MCP Server is running."}), 200

@app.route('/tools', methods=['GET'])
@api_key_required # Apply API key decorator
def list_tools_api():
    if not tool_manager:
        logger.error("Tool manager not available during /tools API request.")
        return jsonify({"error": "Tool manager not available"}), 500
    tools_data = tool_manager.get_all_tools()
    logger.info(f"API /tools authenticated request by {request.remote_addr}. Responding with {len(tools_data)} tools.")
    return jsonify(tools_data), 200

@app.route('/tools/<string:tool_name>/execute', methods=['POST'])
@api_key_required # Apply API key decorator
def execute_tool_api(tool_name):
    if not tool_manager:
        logger.error(f"Tool manager not available for /tools/{tool_name}/execute API request.")
        return jsonify({"error": "Tool manager not available"}), 500

    logger.info(f"API /tools/{tool_name}/execute authenticated request by {request.remote_addr}.")
    tool = tool_manager.get_tool(tool_name)
    if not tool:
        logger.warning(f"API: Attempt to execute non-existent tool '{tool_name}' by {request.remote_addr}.")
        return jsonify({"success": False, "error": f"Tool '{tool_name}' not found."}), 404

    if not request.is_json:
        logger.warning(f"API: Invalid request to execute {tool_name} (not JSON) by {request.remote_addr}.")
        return jsonify({"success": False, "error": "Invalid request: payload must be JSON."}), 400

    params = request.get_json()
    logger.debug(f"API: Executing tool '{tool_name}' with params: {params} (requested by {request.remote_addr})")

    try:
        result = tool_manager.execute_tool(tool_name, params)
        if result.get("success"):
            logger.info(f"API: Tool '{tool_name}' executed successfully by {request.remote_addr}.")
        else:
            logger.warning(f"API: Tool '{tool_name}' execution failed for {request.remote_addr}. Error: {result.get('error')}")
        return jsonify(result), 200 # Result itself contains success status
    except Exception as e:
        logger.error(f"API: Unexpected error executing tool {tool_name} for {request.remote_addr}: {e}", exc_info=True)
        return jsonify({"success": False, "error": "An unexpected server error occurred."}), 500

# === Web Interface Routes ===
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
            password_form = request.form.get('password')

            # Use config_obj here
            cfg_username = config_obj.get('web_auth', {}).get('username')
            hashed_password = config_obj.get('web_auth', {}).get('password_hash')

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
    global config_obj, tool_manager, app # Use config_obj

    logger.info("MCP Server starting up...")
    arg_parser = get_argument_parser()
    args = arg_parser.parse_args()

    loaded_main_config = load_config(args.config)
    final_config = apply_cli_args(loaded_main_config, args)
    config_obj = final_config # Assign to global config_obj

    setup_logging(config_obj.get('logging', {}))
    logger.info(f"Final configuration loaded. Debug mode: {config_obj['server']['debug']}")

    app.secret_key = config_obj.get('server', {}).get('secret_key', app.secret_key)
    if app.secret_key == os.urandom(24) and config_obj['server'].get('enable_web_ui', True):
         logger.warning("Using a default random Flask secret_key. Set a permanent 'secret_key' in config for production if Web UI is enabled.")

    tool_manager = ToolManager(global_config=config_obj)
    logger.info(f"Available tools: {list(tool_manager.get_all_tools().keys())}")

    if config_obj['server'].get('enable_web_ui', True):
        if not config_obj.get('web_auth', {}).get('username') or not config_obj.get('web_auth', {}).get('password_hash'):
            logger.error("Web UI is enabled, but 'web_auth.username' or 'web_auth.password_hash' is missing. Web login will fail.")
        register_web_routes(app)
    else:
        logger.info("Web UI is DISABLED by configuration.")
        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
        def catch_all_disabled_ui(path):
            logger.info(f"Web UI is disabled. Request to '{path}' from {request.remote_addr} resulted in 404.")
            abort(404, description="Web interface is disabled.")

    logger.info(f"MCP Server starting on {config_obj['server']['host']}:{config_obj['server']['port']}. Web UI enabled: {config_obj['server']['enable_web_ui']}. API Auth Token Set: {bool(config_obj.get('api_auth', {}).get('static_token'))}")

    app.run(
        host=config_obj['server']['host'],
        port=config_obj['server']['port'],
        debug=config_obj['server']['debug']
    )
    logger.info("MCP Server shutting down.")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f"Critical error during server startup or main execution: {e}", exc_info=True)
        raise
