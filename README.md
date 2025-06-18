# MCP Server - Multi-Purpose Command and Process Server

MCP Server is a configurable server designed to execute various tools such as scripts, API calls, or other processes. It provides a web interface and an HTTP API for interaction and can be extended with custom tool plugins.

## Features

*   **Extensible Tool Plugins**: Easily add new tools by creating Python plugin classes.
*   **Configurable Tools**: Configure tool behavior and parameters via YAML.
*   **Web Interface**: User-friendly UI for listing, configuring, and executing tools.
    *   Secure login with username and password.
    *   Option to disable the web interface.
*   **HTTP API**: Programmatic access to list and execute tools, secured by token authentication.
*   **Flexible Configuration**: Configure server, authentication (web & API), logging, and tools via YAML file, environment variables, or CLI arguments.
*   **Enhanced Logging**: Multi-level logging to console and rotating log files.
*   **Service Deployment**: Includes documentation for deployment as a systemd service using Gunicorn.

## Getting Started

### Prerequisites

*   Python 3.8+
*   `pip` (Python package installer)
*   `git` (for cloning)

### Installation

1.  **Clone the repository (optional, if you have it as a project):**
    \`\`\`bash
    git clone <your-repo-url> mcp-server
    cd mcp-server
    \`\`\`
    If you downloaded the source directly, navigate to the project root directory.

2.  **Create and activate a virtual environment (recommended):**
    \`\`\`bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    \`\`\`

3.  **Install dependencies:**
    \`\`\`bash
    pip install -r requirements.txt
    \`\`\`

### Configuration

1.  **Create `config/config.yaml`:**
    If it doesn't exist, copy `config/config.yaml.example` (if provided) or create a new one.
    A minimal `config/config.yaml` might look like this:

    \`\`\`yaml
    server:
      host: "0.0.0.0"
      port: 5000
      debug: true # Set to false in production
      enable_web_ui: true
      # IMPORTANT: Change this in your production environment!
      secret_key: "your_very_secret_and_complex_key_for_flask_sessions"

    web_auth:
      username: "admin"
      # Generate a hash for your password (see below)
      password_hash: "pbkdf2:sha256:260000\$yourSalt\$yourHash..."

    api_auth:
      # Static token for API authentication. Generate a secure random string.
      # Example: openssl rand -hex 32
      static_token: "your_secure_api_token_here" # CHANGE THIS!
      # Header name for the API token. Default is 'X-API-KEY'.
      # header_name: "X-API-KEY"

    logging:
      level: "INFO"
      file: "mcp_server.log"
      format: "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
      max_bytes: 10485760 # 10MB
      backup_count: 5

    tools:
      script_runner:
        scripts_base_path: "/app/mcp_scripts" # Path to your scripts
        default_timeout: 60 # Default timeout for scripts
      api_caller:
        default_connect_timeout: 10 # Default connect timeout for API calls
        default_read_timeout: 30    # Default read timeout for API calls
    \`\`\`

2.  **Set `secret_key`**: Update `server.secret_key` in `config/config.yaml` with a long, random string.

3.  **Set Web Authentication Credentials**:
    *   Update `web_auth.username`.
    *   Generate a password hash for `web_auth.password_hash` using the utility:
        \`\`\`bash
        # Ensure your virtual environment is active
        python mcp_server/utils/hash_password.py
        \`\`\`
        Enter your desired password when prompted, and copy the generated hash into `config.yaml`.

4.  **Set API Authentication Token**:
    *   Update `api_auth.static_token` in `config/config.yaml` with a strong, unique, and randomly generated token.
    *   (Optional) Customize `api_auth.header_name` if you prefer a different header for the API token.

### Running the Development Server

\`\`\`bash
# Ensure your virtual environment is active
python mcp_server/app.py --port 5000
\`\`\`
The server will start, and you can access it at \`http://localhost:5000\` (or the configured host/port).

## Configuration Overview

The server is configured primarily through \`config/config.yaml\`. Key sections:
*   **`server`**: Host, port, debug mode, web UI toggle, Flask secret key.
*   **`web_auth`**: Username and hashed password for the web interface.
*   **`api_auth`**: Configuration for API token authentication, including `static_token` and `header_name`.
*   **`logging`**: Log level, file path, format, and rotation settings.
*   **`tools`**: Configuration specific to each loaded tool plugin
    (e.g., `script_runner.default_timeout`, `api_caller.default_connect_timeout`).
    Some tools also support per-execution parameters (e.g., `script_runner` can take a `timeout` in its execution payload).

Settings can also be overridden by environment variables (e.g., \`MCP_SERVER_PORT\`, `MCP_API_STATIC_TOKEN`) or command-line arguments. See comments in `config.py` and `config.yaml` for more details.

## Web Interface

*   **Access**: Navigate to \`http://<your-server-address>:<port>/\`.
*   **Login**: Use the credentials configured in `web_auth`.
*   **Features**: List available tools, view their parameters, execute them, and see the output.

## HTTP API

The server exposes an HTTP API, **which requires token authentication for all endpoints except \`/health\`**.
The API token must be passed in a request header. By default, this is \`X-API-KEY: <your_token>\`.
This can be configured via \`api_auth.header_name\` in \`config.yaml\` (e.g., to use \`Authorization: Bearer <your_token>\`).

Key endpoints:
*   **`GET /tools`**: Lists all available tools, their descriptions, and parameter specifications.
    *   Requires API token authentication.
    Example using \`curl\` (replace \`<token>\` with your actual API token):
    \`\`\`bash
# List tools (using default X-API-KEY header)
curl -H "X-API-KEY: <token>" http://localhost:5000/tools
    \`\`\`
*   **`POST /tools/<tool_name>/execute`**: Executes the specified tool.
    *   Requires API token authentication.
    *   **Request Body (JSON)**: Parameters for the tool.
    *   **Response (JSON)**: Result of the execution, including \`success\` status and \`data\` or \`error\`.
    Example using \`curl\` (replace \`<token>\`, \`script_runner\`, and params):
    \`\`\`bash
# Execute script_runner (using default X-API-KEY header)
curl -X POST -H "Content-Type: application/json" \
     -H "X-API-KEY: <token>" \
     -d '{"script_name": "hello.sh", "arguments": "World", "timeout": 30}' \
     http://localhost:5000/tools/script_runner/execute
    \`\`\`

## Tool Plugins

MCP Server uses a plugin architecture for tools.
*   Plugins are Python classes inheriting from \`mcp_server.tools.base_tool.BaseTool\`.
*   They are located in the \`mcp_server/tools/plugins/\` directory.
*   Each plugin must implement methods like \`get_name()\`, \`get_description()\`, \`get_config_spec()\`, and \`execute()\`.
*   The `api_caller` tool supports configurable default connect and read timeouts, and these can also be overridden per execution.
*   The `script_runner` tool supports a configurable default execution timeout, which can also be overridden per execution.
*   See existing plugins (\`script_runner.py\`, \`api_caller.py\`) as examples.

## Deployment

For production deployments, it is recommended to run the MCP Server as a systemd service using a WSGI server like Gunicorn.
See the detailed [Deployment Guide](docs/deployment.md).

## Running Tests

This project uses \`pytest\` for testing.

1.  **Ensure test dependencies are installed:**
    \`\`\`bash
    pip install pytest pytest-flask pytest-mock pytest-httpserver
    \`\`\`
    (These are included in \`requirements.txt\` if you installed everything.)

2.  **Run tests from the project root directory:**
    \`\`\`bash
    # Ensure your virtual environment is active
    pytest
    \`\`\`
    You can also run specific test files or use other \`pytest\` options:
    \`\`\`bash
    pytest tests/unit/test_config.py
    pytest -k "login"  # Run tests with 'login' in their name
    pytest -v         # Verbose output
    \`\`\`

## License

(Specify your chosen license here, e.g., This project is licensed under the MIT License.)
