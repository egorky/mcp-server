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

## Getting Started: Running MCP Server Locally

This guide will walk you through setting up and running the MCP Server on your local machine for development or testing purposes.

### 1. Prerequisites

*   **Python**: Version 3.8 or newer is required. Verify with \`python3 --version\`.
*   **pip**: The Python package installer. Usually comes with Python.
*   **git**: For cloning the repository (if you're obtaining the code this way).

### 2. Installation

a.  **Clone the Repository (if applicable):**
    If you have the MCP Server code in a git repository:
    \`\`\`bash
    git clone <your-repository-url> mcp-server
    cd mcp-server
    \`\`\`
    If you downloaded the source code directly, navigate to the project's root directory.

b.  **Create and Activate a Python Virtual Environment (Highly Recommended):**
    This keeps your project dependencies isolated.
    \`\`\`bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\\Scripts\\activate
    \`\`\`
    You should see \`(venv)\` at the beginning of your command prompt.

c.  **Install Dependencies:**
    Install all necessary Python packages.
    \`\`\`bash
    pip install -r requirements.txt
    \`\`\`

### 3. Initial Configuration (Critical First Step!)

Before you can run the server, you **must** create and populate a configuration file.

a.  **Create \`config/config.yaml\`:**
    Navigate to the \`config/\` directory within the project. If a \`config.yaml.example\` file exists, you can copy it to \`config.yaml\`. Otherwise, create a new file named \`config.yaml\`.

b.  **Populate Minimum Required Fields:**
    Open \`config/config.yaml\` in a text editor and ensure the following fields are correctly set. These are essential for the server to start and function securely:

    \`\`\`yaml
    server:
      host: "0.0.0.0"  # Or "127.0.0.1" to restrict to local machine
      port: 5000
      debug: true       # Set to false in production
      enable_web_ui: true
      # IMPORTANT: Change this to a long, random, unique string!
      secret_key: "REPLACE_THIS_WITH_A_VERY_SECRET_KEY"

    web_auth:
      username: "admin" # Default username, you can change this
      # IMPORTANT: Generate a password hash for your chosen password (see next step)
      password_hash: "REPLACE_THIS_WITH_GENERATED_PASSWORD_HASH"

    api_auth:
      # IMPORTANT: Generate a secure random token for API access (see next step)
      static_token: "REPLACE_THIS_WITH_YOUR_SECURE_API_TOKEN"
      # Optional: Change if you want to use a different header for the API token
      # header_name: "X-API-KEY" # Default is X-API-KEY
      # Or use:
      # header_name: "Authorization" # Then token should be "Bearer <your_token>"

    logging: # Default logging settings, can be adjusted later
      level: "INFO"
      file: "mcp_server.log"
      # format: "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
      # max_bytes: 10485760 # 10MB
      # backup_count: 5

    tools:
      # Optional: Example tool configuration. Add if you use these tools.
      # script_runner:
      #   scripts_base_path: "/app/mcp_scripts" # Ensure this path exists and is accessible
      #   default_timeout: 60
      # api_caller:
      #   default_connect_timeout: 10
      #   default_read_timeout: 30
    \`\`\`

c.  **Generate Secure Credentials:**

    *   **`server.secret_key`**: Replace \`"REPLACE_THIS_WITH_A_VERY_SECRET_KEY"\` with a long, random string. You can generate one using Python:
        \`python -c 'import secrets; print(secrets.token_hex(32))'\`

    *   **`web_auth.password_hash`**:
        1.  Choose a strong password for the web interface user (\`admin\` or your chosen username).
        2.  Run the provided utility script (make sure your virtual environment is active):
            \`\`\`bash
            python mcp_server/utils/hash_password.py
            \`\`\`
        3.  Enter your chosen password when prompted. The script will output a hash string.
        4.  Copy this entire hash string and replace \`"REPLACE_THIS_WITH_GENERATED_PASSWORD_HASH"\` in your \`config.yaml\`.

    *   **`api_auth.static_token`**:
        1.  Generate a strong, random token for API authentication. You can use a command like:
            \`\`\`bash
            openssl rand -hex 32
            \`\`\`
        2.  Copy this token and replace \`"REPLACE_THIS_WITH_YOUR_SECURE_API_TOKEN"\` in your \`config.yaml\`. **Keep this token secure, like a password.**

### 4. Running the Server Locally (for Development/Testing)

Once your \`config/config.yaml\` is correctly set up:

a.  **Navigate to the project root directory** (where \`mcp_server\` directory and \`requirements.txt\` are located).
b.  **Ensure your virtual environment is active** (\`(venv)\` should be in your prompt).
c.  **Run the application:**
    \`\`\`bash
    python mcp_server/app.py
    \`\`\`
    You can also specify a port if needed (though it's configured in \`config.yaml\`):
    \`\`\`bash
    python mcp_server/app.py --port 5001
    \`\`\`

d.  **Verify it's running:**
    You should see output in your terminal indicating the server has started, similar to:
    \`\`\`
    INFO:mcp_server.app:MCP Server starting on 0.0.0.0:5000. Web UI enabled: True. API Auth Token Set: True
     * Serving Flask app 'app'
     * Debug mode: on  # Or off, depending on your config
    INFO:werkzeug:Werkzeug Dev Server running on http://0.0.0.0:5000/
    Press CTRL+C to quit
    \`\`\`
    (The exact output might vary based on your logging configuration and Flask version.)

e.  **Access the Server:**
    *   **Web Interface**: Open your web browser and go to \`http://localhost:5000\` (or the host/port you configured). Log in with the username and password you set up.
    *   **API**: The API endpoints (e.g., \`/tools\`, \`/tools/<tool_name>/execute\`) are available at the same address. Remember to include your API token in the request headers (see 'HTTP API' section below).

**Important Note on Usage:**
The method described above (\`python mcp_server/app.py\`) uses Flask's built-in development server.
While convenient for local development and testing, it is **not suitable for production environments** due to performance and security limitations.
For production deployment, please refer to the **[Deployment for Production](#deployment-for-production)** section below, which guides you on using a robust WSGI server like Gunicorn and managing the application as a system service.

This local setup is intended for development, testing, and getting familiar with the server. For production use, please refer to the deployment guide.

## Deployment for Production

Running the MCP Server using \`python mcp_server/app.py\` utilizes Flask's built-in development server. **This is NOT suitable for production environments.**

For production deployments, you should:
1.  Use a production-grade WSGI server (like **Gunicorn**, which is included in \`requirements.txt\`).
2.  Run the application as a system service (e.g., using **systemd** on Linux).
3.  Consider using a reverse proxy (like Nginx or Apache) for HTTPS, serving static files, and other benefits.

**Detailed instructions for setting up a production environment are available in the [Deployment Guide](docs/deployment.md).**

## Configuration Overview

The MCP Server is primarily configured via the \`config/config.yaml\` file. This file is organized into several key sections.

The server loads configuration settings in the following order of precedence (each step overrides the previous):
1.  **Default values** hardcoded in the application (`mcp_server/config.py`).
2.  Values from the **\`config/config.yaml\`** file.
3.  Values from **environment variables** (e.g., \`MCP_SERVER_PORT\`, \`MCP_API_STATIC_TOKEN\`).
4.  Values from **command-line arguments** (e.g., \`--port\`, \`--disable-web-ui\`).

This means that environment variables will override settings in \`config.yaml\`, and command-line arguments will override both.
For most persistent settings, you should use \`config/config.yaml\`.

Key configuration sections in \`config/config.yaml\`:
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

To use the API:
1.  **Find your API Token**: The \`static_token\` you configured in \`config/config.yaml\` (under the \`api_auth\` section) or set via the \`MCP_API_STATIC_TOKEN\` environment variable.
2.  **Include the Token in Headers**:
    *   If using the default \`header_name: "X-API-KEY"\` (or if \`header_name\` is set to something custom), add a header like: \`<Your-Header-Name>: <your_static_token>\`.
    *   If you configured \`header_name: "Authorization"\`, add a header like: \`Authorization: Bearer <your_static_token>\`.

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
