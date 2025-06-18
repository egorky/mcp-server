# MCP Server Architecture

## 1. Overview

The MCP (Multi-Purpose Command and Process) Server is a Python-based application designed to provide a centralized and configurable platform for executing various "tools." These tools can range from simple shell scripts to complex API interactions or custom Python processes. The server offers both a web interface (for human users) and an HTTP API (for programmatic access) for managing and triggering these tools.

The architecture emphasizes modularity and extensibility, particularly through its tool plugin system and flexible configuration.

## 2. Key Components

The MCP Server is composed of several key components that work together:

### 2.1. Flask Application (`mcp_server/app.py`)

*   **Core Framework**: Uses [Flask](https://flask.palletsprojects.com/), a lightweight WSGI web application framework.
*   **Responsibilities**:
    *   **Request Handling**: Manages incoming HTTP requests.
    *   **Routing**: Defines URL routes for both the web interface and the HTTP API.
    *   **Web Interface**: Renders HTML templates (using Jinja2) for the user interface, manages user sessions (for login), and handles form submissions.
    *   **API Endpoints**: Implements RESTful API endpoints (e.g., listing and executing tools). These are protected by static token authentication.
    *   **Authentication**:
        *   Handles session-based authentication for the Web UI.
        *   Implements decorator-based static token authentication for the HTTP API.
    *   **Orchestration**: Initializes and integrates other components like the Configuration Manager and Tool Manager during startup.

### 2.2. Configuration Manager (`mcp_server/config.py`)

*   **Purpose**: Handles loading and accessing all server configurations.
*   **Configuration Sources** (in order of precedence, later sources override earlier ones):
    1.  **Default Values**: Hardcoded defaults within `config.py`.
    2.  **YAML File**: Primary configuration file (e.g., \`config/config.yaml\`).
    3.  **Environment Variables**: Allows overriding settings (e.g., \`MCP_SERVER_PORT\`, \`MCP_API_STATIC_TOKEN\`).
    4.  **Command-Line Arguments**: Provides overrides for certain parameters at startup (e.g., \`--port\`).
*   **Responsibilities**:
    *   Merging configurations from multiple sources.
    *   Manages server settings, web UI authentication, **API token authentication**, logging, and tool configurations.
    *   Providing a centralized access point (\`config_obj\` object in `app.py`) for other components.

### 2.3. Tool Manager (`mcp_server/tool_manager.py`)

*   **Purpose**: Manages the lifecycle and execution of tool plugins.
*   **Responsibilities**:
    *   **Plugin Discovery**: Scans the \`mcp_server/tools/plugins/\` directory for valid tool plugin files.
    *   **Plugin Loading**: Imports Python modules and instantiates tool classes that inherit from \`BaseTool\`.
    *   **Tool Registration**: Maintains a registry of available tool instances.
    *   **Parameter Validation**: Performs basic validation of parameters passed for tool execution against the tool's defined \`config_spec\`.
    *   **Execution Dispatch**: Calls the \`execute()\` method of the requested tool instance.
    *   **Configuration Injection**: Passes tool-specific configuration from the global config (e.g., \`config_obj['tools']['my_tool_name']\`) to the tool instance upon initialization.

### 2.4. Tool Plugins (`mcp_server/tools/plugins/` & `mcp_server/tools/base_tool.py`)

*   **`BaseTool` (Abstract Base Class)**: Located in \`mcp_server/tools/base_tool.py\`, it defines the interface that all tool plugins must implement. This includes methods like:
    *   \`get_name()\`: Returns the unique name of the tool.
    *   \`get_description()\`: Provides a human-readable description.
    *   \`get_config_spec()\`: Defines the parameters the tool accepts for execution, including their types, whether they are required, default values, and descriptions. This specification is used for input validation and dynamically generating UI forms.
    *   \`execute(params: dict)\`: The core method that performs the tool's action.
*   **Plugin Modules**: Each tool is typically implemented as a \`.py\` file within the \`mcp_server/tools/plugins/\` directory. Each file can contain one or more classes that inherit from \`BaseTool\`.
    *   Example: `script_runner.py` executes shell scripts. It supports a configurable default execution timeout, which can also be overridden per execution via a 'timeout' parameter.
    *   Example: `api_caller.py` makes HTTP requests. It supports configurable default connect and read timeouts, and these can also be overridden per execution via 'connect_timeout', 'read_timeout', or an overall 'timeout' parameter.
*   **Extensibility**: New tools can be added by creating new plugin files without modifying the core server code.

### 2.5. Logging System (`mcp_server/app.py` - `setup_logging`)

*   **Purpose**: Provides comprehensive logging for diagnostics and monitoring.
*   **Features**:
    *   Uses Python's built-in \`logging\` module.
    *   Configurable log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    *   Configurable log format (e.g., including timestamp, module, line number).
    *   Logging to both console and a file.
    *   **Rotating File Handler**: Automatically manages log file size and backups based on \`max_bytes\` and \`backup_count\`.
    *   Configured via the \`logging\` section in \`config.yaml\`.

### 2.6. Web Interface (Flask Templates & Static Files)

*   **Technology**: Standard HTML, CSS, and JavaScript, rendered by Flask using Jinja2 templating.
*   **Structure**:
    *   **Templates (`mcp_server/templates/`)**: HTML files (\`base.html\`, \`login.html\`, \`dashboard.html\`).
    *   **Static Files (`mcp_server/static/`)**: CSS stylesheets and JavaScript files for client-side interactivity.
*   **Functionality**:
    *   User authentication (login/logout) via sessions.
    *   Dynamically lists available tools by calling the (authenticated) \`/tools\` API.
    *   Dynamically generates forms for tool parameters based on their \`config_spec\`.
    *   Submits tool execution requests to the (authenticated) \`/tools/<tool_name>/execute\` API, passing the API token fetched/stored by the client-side JS (Note: This detail about client-side token handling for Web UI calls to API needs careful implementation if Web UI is to use the same token-protected API).
    *   Displays results from tool execution.

## 3. Data Flow Examples

### 3.1. API Tool Execution

1.  **Client Request**: An HTTP client sends a \`POST\` request to \`/tools/<tool_name>/execute\` with parameters in the JSON body and an API token in the configured header (e.g., \`X-API-KEY\`).
2.  **Flask Routing & Auth**: \`app.py\` routes the request. The \`@api_key_required\` decorator validates the token.
3.  **Tool Manager Invocation**: The handler calls \`tool_manager.execute_tool(tool_name, params)\`.
4.  **Tool Lookup**: \`ToolManager\` finds the registered instance of \`<tool_name>\`.
5.  **Parameter Validation**: \`ToolManager\` validates the provided \`params\` against the tool's \`config_spec\`.
6.  **Tool Execution**: \`ToolManager\` calls the tool's \`execute(validated_params)\` method.
7.  **Plugin Logic**: The tool plugin performs its specific action.
8.  **Result Return**: The plugin returns a result dictionary.
9.  **Response to Client**: The result is returned as a JSON HTTP response.

### 3.2. Web UI Tool Execution

1.  **User Action (Dashboard)**: User (logged in via web auth) selects a tool, fills parameters, clicks "Execute".
2.  **JavaScript Handler**: Client-side JavaScript in \`main.js\` captures form data.
3.  **API Call from JS**: JavaScript sends a \`POST\` request to \`/tools/<tool_name>/execute\`. **Crucially, this request must also include the API token if the Web UI interacts with the same token-protected API endpoints.** The method for the Web UI's JavaScript to obtain and use this API token needs to be defined (e.g., fetched after login, embedded in the page, etc. This has security implications and is not fully detailed in current implementation).
4.  **Backend Processing**: Same as API Tool Execution (steps 2-9 in section 3.1).
5.  **Response to JS**: JSON result returned to JavaScript.
6.  **Display Update**: JavaScript updates the dashboard.

## 4. Configuration Structure (`config.yaml`)

The \`config.yaml\` file is the primary way to configure the server. Its typical structure includes:

\`\`\`yaml
server:
  # Server settings: host, port, debug, enable_web_ui, secret_key
web_auth:
  # Web UI authentication: username, password_hash
api_auth:
  # API authentication: static_token, header_name
logging:
  # Logging configuration: level, file, format, rotation (max_bytes, backup_count)
tools:
  # Tool-specific configurations, keyed by tool name
  script_runner:
    scripts_base_path: "/path/to/scripts"
    default_timeout: 60 # Default script execution timeout
  api_caller:
    default_connect_timeout: 10 # Default connect timeout for API calls
    default_read_timeout: 30    # Default read timeout for API calls
  # my_custom_tool:
  #   api_key: "value"
\`\`\`

## 5. Design Choices & Rationale

*   **Flask**: Chosen for its simplicity, flexibility, and minimal boilerplate.
*   **Plugin Architecture for Tools**: For modularity and extensibility.
*   **YAML for Configuration**: Human-readable and common for configuration.
*   **Standard Python Logging**: Robust and familiar.
*   **Separate Auth for Web UI & API**: Web UI uses sessions/cookies; API uses a static token. This is a common pattern.

## 6. Future Enhancements/Considerations (Optional)

*   **Asynchronous Tool Execution**: For long-running tools (e.g., using Celery).
*   **Advanced Parameter Types**: E.g., file uploads in \`config_spec\`.
*   **Dynamic API Token Management**: Instead of a single static token.
*   **Web UI API Token Handling**: Clarify how JavaScript running in the Web UI securely obtains and uses the API token when making calls to the backend API.
*   **Database Integration**: For execution history, more complex user/tool management.
*   **RBAC**: More granular permissions for tools.
