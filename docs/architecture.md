# MCP Server Architecture

## 1. Overview

The MCP (Multi-Purpose Command and Process) Server is a Python-based application designed to provide a centralized and configurable platform for executing various "tools." These tools can range from simple shell scripts to complex API interactions or custom Python processes. The server offers both a web interface and an HTTP API for managing and triggering these tools.

The architecture emphasizes modularity and extensibility, particularly through its tool plugin system.

## 2. Key Components

The MCP Server is composed of several key components that work together:

### 2.1. Flask Application (`mcp_server/app.py`)

*   **Core Framework**: Uses [Flask](https://flask.palletsprojects.com/), a lightweight WSGI web application framework.
*   **Responsibilities**:
    *   **Request Handling**: Manages incoming HTTP requests.
    *   **Routing**: Defines URL routes for both the web interface and the HTTP API.
    *   **Web Interface**: Renders HTML templates (using Jinja2) for the user interface, manages user sessions, and handles form submissions.
    *   **API Endpoints**: Implements RESTful API endpoints for programmatic interaction (e.g., listing and executing tools).
    *   **Orchestration**: Initializes and integrates other components like the Configuration Manager and Tool Manager during startup.

### 2.2. Configuration Manager (`mcp_server/config.py`)

*   **Purpose**: Handles loading and accessing server configuration.
*   **Configuration Sources**:
    1.  **Default Values**: Hardcoded defaults within `config.py`.
    2.  **YAML File**: Primary configuration file (e.g., \`config/config.yaml\`).
    3.  **Environment Variables**: Allows overriding settings (e.g., \`MCP_SERVER_PORT\`).
    4.  **Command-Line Arguments**: Provides overrides for certain parameters at startup (e.g., \`--port\`).
*   **Responsibilities**:
    *   Merging configurations from multiple sources in a defined order of precedence.
    *   Providing a centralized access point (\`config\` object) for other components.

### 2.3. Tool Manager (`mcp_server/tool_manager.py`)

*   **Purpose**: Manages the lifecycle and execution of tool plugins.
*   **Responsibilities**:
    *   **Plugin Discovery**: Scans the \`mcp_server/tools/plugins/\` directory for valid tool plugin files.
    *   **Plugin Loading**: Imports Python modules and instantiates tool classes that inherit from \`BaseTool\`.
    *   **Tool Registration**: Maintains a registry of available tool instances.
    *   **Parameter Validation**: Performs basic validation of parameters passed for tool execution against the tool's defined \`config_spec\`.
    *   **Execution Dispatch**: Calls the \`execute()\` method of the requested tool instance.
    *   **Configuration Injection**: Passes tool-specific configuration from the global config (e.g., \`config['tools']['my_tool_name']\`) to the tool instance upon initialization.

### 2.4. Tool Plugins (`mcp_server/tools/plugins/` & `mcp_server/tools/base_tool.py`)

*   **`BaseTool` (Abstract Base Class)**: Located in \`mcp_server/tools/base_tool.py\`, it defines the interface that all tool plugins must implement. This includes methods like:
    *   \`get_name()\`: Returns the unique name of the tool.
    *   \`get_description()\`: Provides a human-readable description.
    *   \`get_config_spec()\`: Defines the parameters the tool accepts for execution, including their types, whether they are required, default values, and descriptions. This specification is used for input validation and dynamically generating UI forms.
    *   \`execute(params: dict)\`: The core method that performs the tool's action.
*   **Plugin Modules**: Each tool is typically implemented as a \`.py\` file within the \`mcp_server/tools/plugins/\` directory. Each file can contain one or more classes that inherit from \`BaseTool\`.
*   **Extensibility**: New tools can be added by creating new plugin files without modifying the core server code.

### 2.5. Logging System (`mcp_server/app.py` - `setup_logging`)

*   **Purpose**: Provides comprehensive logging for diagnostics and monitoring.
*   **Features**:
    *   Uses Python's built-in \`logging\` module.
    *   Configurable log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    *   Configurable log format.
    *   Logging to both console and a file.
    *   **Rotating File Handler**: Automatically manages log file size and backups.
    *   Configured via the \`logging\` section in \`config.yaml\`.

### 2.6. Web Interface (Flask Templates & Static Files)

*   **Technology**: Standard HTML, CSS, and JavaScript, rendered by Flask using Jinja2 templating.
*   **Structure**:
    *   **Templates (`mcp_server/templates/`)**: HTML files (\`base.html\`, \`login.html\`, \`dashboard.html\`).
    *   **Static Files (`mcp_server/static/`)**: CSS stylesheets and JavaScript files for client-side interactivity.
*   **Functionality**:
    *   User authentication (login/logout).
    *   Dynamically lists available tools by calling the \`/tools\` API.
    *   Dynamically generates forms for tool parameters based on their \`config_spec\`.
    *   Submits tool execution requests to the \`/tools/<tool_name>/execute\` API.
    *   Displays results from tool execution.

## 3. Data Flow Examples

### 3.1. API Tool Execution

1.  **Client Request**: An HTTP client sends a \`POST\` request to \`/tools/<tool_name>/execute\` with parameters in the JSON body.
2.  **Flask Routing**: \`app.py\` routes the request to the \`execute_tool_api\` handler function.
3.  **Tool Manager Invocation**: The handler calls \`tool_manager.execute_tool(tool_name, params)\`.
4.  **Tool Lookup**: \`ToolManager\` finds the registered instance of \`<tool_name>\`.
5.  **Parameter Validation**: \`ToolManager\` validates the provided \`params\` against the tool's \`config_spec\`.
6.  **Tool Execution**: \`ToolManager\` calls the tool's \`execute(validated_params)\` method.
7.  **Plugin Logic**: The tool plugin performs its specific action (e.g., runs a script, calls an external API).
8.  **Result Return**: The plugin returns a result dictionary (e.g., \`{"success": True, "data": ...}\`).
9.  **Response to Client**: The result is passed back through \`ToolManager\` and the Flask handler, finally returned to the client as a JSON HTTP response.

### 3.2. Web UI Tool Execution

1.  **User Action (Dashboard)**: User selects a tool, fills in parameters, and clicks "Execute".
2.  **JavaScript Handler**: Client-side JavaScript in \`main.js\` captures the form data.
3.  **API Call from JS**: JavaScript constructs a JSON payload and sends a \`POST\` request to \`/tools/<tool_name>/execute\` (similar to the API flow above).
4.  **Backend Processing**: The request is processed by the API endpoint as described in section 3.1.
5.  **Response to JS**: The JSON result is returned to the JavaScript \`fetch\` call.
6.  **Display Update**: JavaScript updates the "Output" section of the dashboard with the formatted result.

## 4. Configuration Structure (`config.yaml`)

The \`config.yaml\` file is the primary way to configure the server. Its typical structure includes:

\`\`\`yaml
server:
  # Server settings: host, port, debug, enable_web_ui, secret_key
web_auth:
  # Web UI authentication: username, password_hash
logging:
  # Logging configuration: level, file, format, rotation (max_bytes, backup_count)
tools:
  # Tool-specific configurations, keyed by tool name
  script_runner:
    scripts_base_path: "/path/to/scripts"
    default_timeout: 60
  api_caller:
    default_timeout: 30
  # my_custom_tool:
  #   api_key: "value"
\`\`\`

## 5. Design Choices & Rationale

*   **Flask**: Chosen for its simplicity, flexibility, and minimal boilerplate, making it suitable for building both a web UI and an API.
*   **Plugin Architecture for Tools**: Provides excellent modularity and extensibility. New functionalities can be added without altering core server code, promoting separation of concerns.
*   **YAML for Configuration**: Human-readable and widely used for configuration files.
*   **Standard Python Logging**: Leverages a robust and familiar logging framework.

## 6. Future Enhancements/Considerations (Optional)

*   **Asynchronous Tool Execution**: For long-running tools, implement task queues (e.g., Celery, RQ) to prevent blocking API/web requests.
*   **More Sophisticated Parameter Types**: Extend \`config_spec\` to support more complex types (lists, objects, file uploads).
*   **Tool-Specific UI**: Allow tools to provide custom HTML snippets for rendering their parameters or results in the web UI.
*   **Real-time Log Streaming**: Stream tool execution logs to the web UI in real-time (e.g., using WebSockets).
*   **API Authentication**: Implement token-based authentication (e.g., API keys, OAuth2) for the HTTP API.
*   **Database Integration**: For storing tool execution history, user data (if more complex user management is needed), or tool configurations.
*   **More Granular Permissions**: Role-based access control (RBAC) for accessing or executing specific tools.
