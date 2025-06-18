# MCP Server - Multi-Purpose Command and Process Server

MCP Server is a configurable server designed to execute various tools such as scripts, API calls, or other processes. It provides a web interface and an HTTP API for interaction and can be extended with custom tool plugins.

## Features

*   **Extensible Tool Plugins**: Easily add new tools by creating Python plugin classes.
*   **Configurable Tools**: Configure tool behavior and parameters via YAML.
*   **Web Interface**: User-friendly UI for listing, configuring, and executing tools.
    *   Secure login with username and password.
    *   Option to disable the web interface.
*   **HTTP API**: Programmatic access to list and execute tools.
*   **Flexible Configuration**: Configure server, authentication, logging, and tools via YAML file, environment variables, or CLI arguments.
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

    logging:
      level: "INFO"
      file: "mcp_server.log"
      format: "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
      max_bytes: 10485760 # 10MB
      backup_count: 5

    tools:
      # Example: Configure the script_runner tool if you have scripts in /app/mcp_scripts
      # script_runner:
      #   scripts_base_path: "/app/mcp_scripts"
      #   default_timeout: 60
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
*   **`logging`**: Log level, file path, format, and rotation settings.
*   **`tools`**: Configuration specific to each loaded tool plugin (e.g., `script_runner.scripts_base_path`).

Settings can also be overridden by environment variables (e.g., \`MCP_SERVER_PORT\`) or command-line arguments. See comments in `config.py` and `config.yaml` for more details.

## Web Interface

*   **Access**: Navigate to \`http://<your-server-address>:<port>/\`.
*   **Login**: Use the credentials configured in `web_auth`.
*   **Features**: List available tools, view their parameters, execute them, and see the output.

## HTTP API

The server exposes a simple HTTP API:

*   **`GET /tools`**: Lists all available tools, their descriptions, and parameter specifications.
*   **`POST /tools/<tool_name>/execute`**: Executes the specified tool.
    *   **Request Body (JSON)**: Parameters for the tool.
    *   **Response (JSON)**: Result of the execution, including \`success\` status and \`data\` or \`error\`.

Example using \`curl\` (replace \`yourtool\` and params):
\`\`\`bash
# List tools
curl http://localhost:5000/tools

# Execute a tool (e.g., script_runner with a script named 'hello.sh')
curl -X POST -H "Content-Type: application/json" \
     -d '{"script_name": "hello.sh", "arguments": "World"}' \
     http://localhost:5000/tools/script_runner/execute
\`\`\`

## Tool Plugins

MCP Server uses a plugin architecture for tools.
*   Plugins are Python classes inheriting from \`mcp_server.tools.base_tool.BaseTool\`.
*   They are located in the \`mcp_server/tools/plugins/\` directory.
*   Each plugin must implement methods like \`get_name()\`, \`get_description()\`, \`get_config_spec()\`, and \`execute()\`.
*   See existing plugins (\`script_runner.py\`, \`api_caller.py\`) as examples.

## Deployment

For production deployments, it is recommended to run the MCP Server as a systemd service using a WSGI server like Gunicorn.
See the detailed [Deployment Guide](docs/deployment.md).

## Running Tests (Placeholder)

(Instructions for running tests will be added once tests are implemented in Step 10.)
\`\`\`bash
# Example: pytest tests/
\`\`\`

## License

(Specify your chosen license here, e.g., This project is licensed under the MIT License.)
