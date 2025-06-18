import requests
import logging
from mcp_server.tools.base_tool import BaseTool
import json

logger = logging.getLogger(__name__)

class ApiCallerTool(BaseTool):

    @staticmethod
    def get_name() -> str:
        return "api_caller"

    def get_description(self) -> str:
        return "Makes an HTTP request. Supports distinct connect & read timeouts."

    def get_config_spec(self) -> dict:
        return {
            "url": {"type": "string", "required": True, "description": "The URL to call."},
            "method": {"type": "string", "required": True, "default": "GET", "description": "HTTP method (GET, POST, PUT, DELETE, etc.)."},
            "headers": {"type": "string", "required": False, "description": "JSON string of headers (e.g., '{\"Authorization\": \"Bearer token\"}')."},
            "params": {"type": "string", "required": False, "description": "JSON string of URL query parameters."},
            "json_body": {"type": "string", "required": False, "description": "JSON string for the request body (for POST, PUT)."},
            "timeout": {"type": "integer", "required": False, "description": "Overall request timeout in seconds (sets both connect and read if specific ones are not set)."},
            "connect_timeout": {"type": "integer", "required": False, "description": "Connection timeout in seconds."},
            "read_timeout": {"type": "integer", "required": False, "description": "Read timeout in seconds (from first byte received)."}
        }

    def _determine_timeout(self, params: dict) -> tuple | float | None:
        """Determines the timeout configuration for the request library."""
        connect_timeout_param = params.get("connect_timeout")
        read_timeout_param = params.get("read_timeout")
        overall_timeout_param = params.get("timeout")

        # Get defaults from tool config (e.g., config.yaml -> tools.api_caller section)
        default_connect_timeout = self.config.get("default_connect_timeout", 10) # Default 10s for connect
        default_read_timeout = self.config.get("default_read_timeout", 30)    # Default 30s for read
        default_overall_timeout = self.config.get("default_timeout")          # General default from previous version

        final_connect_timeout = default_connect_timeout
        final_read_timeout = default_read_timeout

        if connect_timeout_param is not None:
            final_connect_timeout = float(connect_timeout_param)
        if read_timeout_param is not None:
            final_read_timeout = float(read_timeout_param)

        # If specific timeouts are set (either by param or by new defaults), use them as a tuple
        if connect_timeout_param is not None or read_timeout_param is not None or \
           self.config.get("default_connect_timeout") is not None or \
           self.config.get("default_read_timeout") is not None:
            logger.debug(f"Using separate timeouts: connect={final_connect_timeout}s, read={final_read_timeout}s")
            return (final_connect_timeout, final_read_timeout)

        # Fallback to overall timeout (param or old default)
        if overall_timeout_param is not None:
            logger.debug(f"Using overall timeout (param): {float(overall_timeout_param)}s for connect and read")
            return float(overall_timeout_param)

        if default_overall_timeout is not None: # Old default from tool config
            logger.debug(f"Using overall timeout (tool config default): {float(default_overall_timeout)}s for connect and read")
            return float(default_overall_timeout)

        # If no timeouts specified anywhere, but we have new defaults, use them.
        # This case is covered above. If all are None, requests might use its own defaults or no timeout.
        # Explicitly return the tuple of new defaults if nothing else was specified.
        logger.debug(f"Falling back to default separate timeouts: connect={final_connect_timeout}s, read={final_read_timeout}s")
        return (final_connect_timeout, final_read_timeout)


    def execute(self, params: dict) -> dict:
        url = params.get("url")
        method = params.get("method", "GET").upper()

        try:
            headers_str = params.get("headers")
            headers = json.loads(headers_str) if headers_str else {}
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in headers for API call to {url}: {e}")
            return {"success": False, "error": f"Invalid JSON in headers: {e}"}

        try:
            params_str = params.get("params")
            query_params = json.loads(params_str) if params_str else {}
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in query params for API call to {url}: {e}")
            return {"success": False, "error": f"Invalid JSON in params: {e}"}

        try:
            json_body_str = params.get("json_body")
            json_data = json.loads(json_body_str) if json_body_str else None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in json_body for API call to {url}: {e}")
            return {"success": False, "error": f"Invalid JSON in json_body: {e}"}

        timeout_config = self._determine_timeout(params)

        logger.info(f"Calling API: {method} {url} with headers={headers}, params={query_params}, json_body={json_data}, timeout_config={timeout_config}")

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                params=query_params,
                json=json_data,
                timeout=timeout_config
            )
            response.raise_for_status()

            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text # Fallback to text if not JSON

            logger.info(f"API call to {url} successful. Status: {response.status_code}")
            return {"success": True, "data": {"status_code": response.status_code, "response": response_data, "headers": dict(response.headers)}}

        except requests.exceptions.Timeout as e: # Catches both ConnectTimeout and ReadTimeout
            timeout_type = "Unknown"
            if isinstance(e, requests.exceptions.ConnectTimeout):
                timeout_type = "Connection"
            elif isinstance(e, requests.exceptions.ReadTimeout):
                timeout_type = "Read"
            logger.error(f"API call to {url} timed out ({timeout_type} timeout). Config: {timeout_config}. Error: {e}")
            return {"success": False, "error": f"API call {timeout_type.lower()} timed out.", "details": str(e)}
        except requests.exceptions.HTTPError as e:
            logger.error(f"API call to {url} failed with HTTPError: {e.response.status_code} - {e.response.text}")
            return {"success": False, "error": f"API Error: {e.response.status_code}", "data": {"response": e.response.text if e.response else 'No response body', "status_code": e.response.status_code if e.response else 'N/A'}}
        except requests.exceptions.RequestException as e: # Catchall for other requests errors (DNS failure, Connection refused etc.)
            logger.error(f"Error calling API {url}: {e}", exc_info=True)
            return {"success": False, "error": f"An unexpected error occurred during API call: {str(e)}"}
