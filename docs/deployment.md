# MCP Server Deployment Guide

This guide provides instructions for deploying the MCP (Multi-Purpose Command and Process) Server as a systemd service on a Linux system. We recommend using a production-grade WSGI server like Gunicorn.

## 1. Prerequisites

*   **Linux System**: A modern Linux distribution that uses systemd.
*   **Python**: Python 3.8 or newer.
*   **pip**: Python package installer.
*   **git**: For cloning the repository.
*   **Virtual Environment (Recommended)**: `venv` module (usually included with Python) or `virtualenv`.

## 2. Installation and Setup

### 2.1. Clone the Repository (if applicable)
If you have the MCP Server code in a git repository:
\`\`\`bash
git clone <your-repository-url> /opt/mcp-server
cd /opt/mcp-server
\`\`\`
Replace \`/opt/mcp-server\` with your desired installation directory. We'll use this path as an example throughout the guide.

### 2.2. Create a Dedicated User (Recommended)
For security, run the server under a dedicated non-root user:
\`\`\`bash
sudo useradd --system --no-create-home mcpuser
# Add user to a group if needed, e.g., to access specific script directories
# sudo usermod -a -G yourgroup mcpuser
\`\`\`

### 2.3. Set Up Python Virtual Environment
\`\`\`bash
cd /opt/mcp-server
python3 -m venv venv
source venv/bin/activate
\`\`\`

### 2.4. Install Dependencies
\`\`\`bash
pip install -r requirements.txt
\`\`\`
This will install Flask, Gunicorn, PyYAML, and other necessary packages.

### 2.5. Configure the MCP Server

#### a. Create Configuration File
Copy or create your configuration file at \`/opt/mcp-server/config/config.yaml\`. Start with the provided \`config.yaml.example\` or ensure your configuration is complete.

**Important Configuration Values:**

*   **`server.secret_key`**: Set a long, random, and unique string for Flask session security.
*   **`web_auth.username`**: The username for web interface login.
*   **`web_auth.password_hash`**: The hashed password for the web user. Generate this using the provided utility:
    \`\`\`bash
    # Ensure virtual environment is active
    # source /opt/mcp-server/venv/bin/activate
    python /opt/mcp-server/mcp_server/utils/hash_password.py
    \`\`\`
    Copy the generated hash into your `config.yaml`.
*   **`logging.file`**: Ensure the path is absolute (e.g., \`/var/log/mcp-server/mcp_server.log\`) and the \`mcpuser\` has write permissions to the directory.
*   **`tools.script_runner.scripts_base_path`**: If using the script runner tool, ensure this path is correctly set and \`mcpuser\` has appropriate permissions to access/execute scripts within it.

#### b. Set File Permissions
Ensure the \`mcpuser\` can read the configuration and write to the log directory/file:
\`\`\`bash
sudo chown -R mcpuser:mcpuser /opt/mcp-server
sudo mkdir -p /var/log/mcp-server
sudo chown mcpuser:mcpuser /var/log/mcp-server
# If scripts_base_path is outside /opt/mcp-server, adjust its permissions too.
\`\`\`
**Note:** Be careful with permissions on your configuration file if it contains sensitive information.

## 3. Systemd Service Configuration

### 3.1. Create the Service File
Create a systemd service file named \`mcp-server.service\` in \`/etc/systemd/system/\`:

\`\`\`bash
sudo nano /etc/systemd/system/mcp-server.service
\`\`\`

Paste the following content into the file. Adjust paths and settings as necessary.

\`\`\`ini
[Unit]
Description=MCP Server - Multi-Purpose Command and Process Server
After=network.target

[Service]
User=mcpuser
Group=mcpuser # Or a relevant group

# Working directory for the application
WorkingDirectory=/opt/mcp-server

# Command to start the server using Gunicorn
# Ensure the path to gunicorn and app.py (or module:app) are correct
# The path to gunicorn should be from the virtual environment
ExecStart=/opt/mcp-server/venv/bin/gunicorn --workers 3     --bind unix:/run/mcp-server/mcp-server.sock     --log-level info     --access-logfile /var/log/mcp-server/gunicorn.access.log     --error-logfile /var/log/mcp-server/gunicorn.error.log     'mcp_server.app:app'

# Alternatively, to bind to a TCP port (e.g., 5000) directly:
# ExecStart=/opt/mcp-server/venv/bin/gunicorn --workers 3 #     --bind 0.0.0.0:5000 #     'mcp_server.app:app'
# Make sure the port matches your config.yaml or that Gunicorn overrides it.

# Environment variables (if needed, e.g., for MCP_CONFIG_PATH)
# Environment="MCP_CONFIG_PATH=/opt/mcp-server/config/config.yaml"
# Environment="FLASK_ENV=production" # Good practice

# Restart policy
Restart=always
RestartSec=5s

# Standard output and error
# If using Gunicorn's log files, journald might primarily capture Gunicorn's own startup/shutdown messages.
# If Gunicorn logs to stdout/stderr (default if no log files specified), journald captures app logs.
StandardOutput=journal
StandardError=journal

# Ensure the /run directory for the socket exists if using UNIX socket
# This can be handled by a tmpfiles.d configuration or by creating it manually
# and ensuring mcpuser has write access.
# Example for tmpfiles.d (create /etc/tmpfiles.d/mcp-server.conf):
# d /run/mcp-server 0755 mcpuser mcpuser -
RuntimeDirectory=mcp-server
RuntimeDirectoryMode=0755


[Install]
WantedBy=multi-user.target
\`\`\`

**Explanation of `ExecStart` options:**
*   `--workers 3`: Number of Gunicorn worker processes. Adjust based on your server's CPU cores (e.g., `2 * num_cores + 1`).
*   `--bind unix:/run/mcp-server/mcp-server.sock`: Bind to a UNIX socket. This is common if you're using a reverse proxy like Nginx or Apache. Ensure the `/run/mcp-server` directory is created (systemd's `RuntimeDirectory` helps here) and `mcpuser` has write access.
*   `--bind 0.0.0.0:5000`: Alternatively, bind to a TCP port.
*   `--log-level info`: Gunicorn's log level.
*   `--access-logfile` & `--error-logfile`: Paths for Gunicorn's logs. Ensure `mcpuser` can write here.
*   `'mcp_server.app:app'`: Path to your Flask application instance (`app`) within your module (`mcp_server.app`).

### 3.2. Reload Systemd, Enable and Start the Service
\`\`\`bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-server.service
sudo systemctl start mcp-server.service
\`\`\`

### 3.3. Check Service Status and Logs
\`\`\`bash
sudo systemctl status mcp-server.service
\`\`\`
To view logs (if `StandardOutput=journal`):
\`\`\`bash
sudo journalctl -u mcp-server.service -f
\`\`\`
If Gunicorn logs to files, check those files (e.g., \`/var/log/mcp-server/\`). The application's own logs (from `logging.file` in `config.yaml`) will also be in their configured location.

## 4. Reverse Proxy (Recommended for Production)

For production, especially if exposing the server to the internet, it's highly recommended to use a reverse proxy like Nginx or Apache. The reverse proxy can handle:
*   HTTPS (SSL/TLS termination)
*   Serving static files directly
*   Load balancing (if you scale to multiple instances)
*   Request buffering and rate limiting

### Example Nginx Configuration (if Gunicorn uses a UNIX socket)

Create an Nginx site configuration (e.g., \`/etc/nginx/sites-available/mcp-server\`)

\`\`\`nginx
server {
    listen 80;
    server_name your_domain.com; # Or IP address

    # Redirect HTTP to HTTPS (if you have SSL)
    # location / {
    #     return 301 https://\$host\$request_uri;
    # }

    # For SSL (uncomment and configure if you have certs)
    # listen 443 ssl;
    # ssl_certificate /path/to/your/fullchain.pem;
    # ssl_certificate_key /path/to/your/privkey.pem;
    # include snippets/ssl-params.conf; # Your SSL parameters

    location /static {
        alias /opt/mcp-server/mcp_server/static; # Path to your static files
        expires 30d;
    }

    location / {
        proxy_pass http://unix:/run/mcp-server/mcp-server.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
\`\`\`
Enable the site: \`sudo ln -s /etc/nginx/sites-available/mcp-server /etc/nginx/sites-enabled/\` and restart Nginx: \`sudo systemctl restart nginx\`.

## 5. Important Considerations

*   **Security**:
    *   Run as a non-root user (\`mcpuser\`).
    *   Keep your system and dependencies updated.
    *   Use a firewall (e.g., \`ufw\`) to restrict access to necessary ports.
    *   Ensure your \`config.yaml\` (especially \`secret_key\` and password hash) is secure and has restricted read access.
*   **Logging**:
    *   Application logs are configured in \`config.yaml\` (\`logging.file\`).
    *   Gunicorn logs can be configured in the systemd service file or a Gunicorn config file.
    *   Systemd journal (via \`journalctl\`) captures service stdout/stderr.
*   **Configuration Management**: For production, consider how you manage \`config.yaml\`. Avoid committing sensitive data directly to version control if the repository is public or shared. Use environment variables (as supported by \`config.py\`) or a secure configuration management tool.
*   **Resource Limits**: You can set resource limits (CPU, memory) in the systemd service file if needed.

This guide provides a comprehensive starting point. Adapt it to your specific environment and security requirements.
