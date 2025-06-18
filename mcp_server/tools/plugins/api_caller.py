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
        return "Makes an HTTP request to a specified URL. Supports GET, POST, PUT, DELETE. Configure 'default_timeout' in general tool config."

    def get_config_spec(self) -> dict:
        return {
            "url": {"type": "string", "required": True, "description": "The URL to call."},
            "method": {"type": "string", "required": True, "default": "GET", "description": "HTTP method (GET, POST, PUT, DELETE, etc.)."},
            "headers": {"type": "string", "required": False, "description": "JSON string of headers (e.g., '{\"Authorization\": \"Bearer token\"}')."},
            "params": {"type": "string", "required": False, "description": "JSON string of URL query parameters."},
            "json_body": {"type": "string", "required": False, "description": "JSON string for the request body (for POST, PUT)."},
            "timeout": {"type": "integer", "required": False, "description": "Request timeout in seconds."}
        }

    def execute(self, params: dict) -> dict:
        url = params.get("url")
        method = params.get("method", "GET").upper()

        try:
            headers_str = params.get("headers")
            headers = json.loads(headers_str) if headers_str else {}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON in headers: {e}"}

        try:
            params_str = params.get("params")
            query_params = json.loads(params_str) if params_str else {}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON in params: {e}"}

        try:
            json_body_str = params.get("json_body")
            json_data = json.loads(json_body_str) if json_body_str else None
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON in json_body: {e}"}

        timeout = params.get("timeout", self.config.get("default_timeout", 30))

        logger.info(f"Calling API: {method} {url} with headers={headers}, params={query_params}, json_body={json_data}, timeout={timeout}")

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                params=query_params,
                json=json_data, # requests handles serialization if this is a dict
                timeout=timeout
            )
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text

            logger.info(f"API call to {url} successful. Status: {response.status_code}")
            return {"success": True, "data": {"status_code": response.status_code, "response": response_data, "headers": dict(response.headers)}}
        except requests.exceptions.HTTPError as e:
            logger.error(f"API call to {url} failed with HTTPError: {e.response.status_code} - {e.response.text}")
            return {"success": False, "error": f"API Error: {e.response.status_code}", "data": {"response": e.response.text, "status_code": e.response.status_code}}
        except requests.exceptions.Timeout:
            logger.error(f"API call to {url} timed out after {timeout} seconds.")
            return {"success": False, "error": "API call timed out."}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling API {url}: {e}", exc_info=True)
            return {"success": False, "error": f"An unexpected error occurred during API call: {str(e)}"}
