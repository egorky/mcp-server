import yaml
import os
import argparse
import logging
from dotenv import load_dotenv

load_dotenv()

DEFAULT_CONFIG_PATH = 'config/config.yaml'

def load_config(config_path=None):
    path = config_path or os.getenv('MCP_CONFIG_PATH') or DEFAULT_CONFIG_PATH

    config = {
        'server': {
            'host': '0.0.0.0',
            'port': 5000,
            'debug': False,
            'enable_web_ui': True,
            'secret_key': 'default_fallback_secret_key_change_me'
        },
        'web_auth': {
            'username': 'admin',
            'password_hash': None,
        },
        'logging': {
            'level': 'INFO',
            'file': 'mcp_server.log',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'max_bytes': 1024 * 1024 * 5,  # 5 MB
            'backup_count': 3,
        },
        'tools': {}
    }

    try:
        with open(path, 'r') as f:
            file_config = yaml.safe_load(f)
            if file_config:
                for key, value in file_config.items():
                    if isinstance(value, dict) and key in config:
                        # Ensure nested logging settings are updated, not overwritten
                        if key == 'logging' and 'logging' in file_config:
                             config['logging'].update(file_config['logging'])
                        else:
                            config[key].update(value)
                    else:
                        config[key] = value
        logging.info(f"Configuration loaded from {path}")
    except FileNotFoundError:
        logging.warning(f"Configuration file not found at {path}. Using default settings and environment variables.")
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML configuration file {path}: {e}")

    # Override with environment variables
    config['server']['host'] = os.getenv('MCP_SERVER_HOST', config['server']['host'])
    config['server']['port'] = int(os.getenv('MCP_SERVER_PORT', config['server']['port']))
    config['server']['debug'] = os.getenv('MCP_SERVER_DEBUG', str(config['server']['debug'])).lower() == 'true'
    config['server']['enable_web_ui'] = os.getenv('MCP_ENABLE_WEB_UI', str(config['server']['enable_web_ui'])).lower() == 'true'
    config['server']['secret_key'] = os.getenv('MCP_SECRET_KEY', config['server']['secret_key'])

    config['web_auth']['username'] = os.getenv('MCP_WEB_USERNAME', config['web_auth']['username'])
    config['web_auth']['password_hash'] = os.getenv('MCP_WEB_PASSWORD_HASH', config['web_auth']['password_hash'])

    config['logging']['level'] = os.getenv('MCP_LOG_LEVEL', config['logging']['level']).upper()
    config['logging']['file'] = os.getenv('MCP_LOG_FILE', config['logging']['file'])
    config['logging']['format'] = os.getenv('MCP_LOG_FORMAT', config['logging']['format'])
    config['logging']['max_bytes'] = int(os.getenv('MCP_LOG_MAX_BYTES', config['logging']['max_bytes']))
    config['logging']['backup_count'] = int(os.getenv('MCP_LOG_BACKUP_COUNT', config['logging']['backup_count']))

    return config

def get_argument_parser():
    parser = argparse.ArgumentParser(description="MCP Server")
    parser.add_argument('--config', type=str, help=f"Path to the configuration file (default: {DEFAULT_CONFIG_PATH})")
    parser.add_argument('--port', type=int, help="Server port (overrides config)")
    parser.add_argument('--host', type=str, help="Server host (overrides config)")
    parser.add_argument('--disable-web-ui', action='store_true', help="Disable web interface")
    parser.add_argument('--enable-web-ui', action='store_true', help="Enable web interface")
    parser.add_argument('--debug', action='store_true', help="Enable debug mode")
    return parser

def apply_cli_args(config, args):
    if args.host: config['server']['host'] = args.host
    if args.port: config['server']['port'] = args.port
    if args.debug: config['server']['debug'] = True
    if args.enable_web_ui: config['server']['enable_web_ui'] = True
    elif args.disable_web_ui: config['server']['enable_web_ui'] = False
    return config
