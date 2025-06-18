import os
import importlib
import inspect
import logging
from mcp_server.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class ToolManager:
    def __init__(self, plugin_dir="mcp_server/tools/plugins", global_config=None):
        self.plugin_dir = plugin_dir
        self.tools = {} # Stores instances of loaded tools
        self.global_config = global_config if global_config else {}
        self._discover_plugins()

    def _discover_plugins(self):
        logger.info(f"Discovering plugins in: {os.path.abspath(self.plugin_dir)}")
        if not os.path.isdir(self.plugin_dir):
            logger.warning(f"Plugin directory {self.plugin_dir} not found.")
            return

        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                module_path = f"{self.plugin_dir.replace('/', '.')}.{module_name}"
                try:
                    module = importlib.import_module(module_path)
                    for name, cls in inspect.getmembers(module, inspect.isclass):
                        if issubclass(cls, BaseTool) and cls is not BaseTool:
                            # Pass the tool-specific part of the global config if available
                            tool_config_key = cls.get_name(cls) # Call get_name statically for config key
                            tool_specific_config = self.global_config.get('tools', {}).get(tool_config_key, {})

                            tool_instance = cls(config=tool_specific_config)
                            tool_name = tool_instance.get_name() # Instance method call
                            if tool_name in self.tools:
                                logger.warning(f"Tool name conflict: {tool_name} already loaded. Skipping {module_path}.{name}")
                            else:
                                self.tools[tool_name] = tool_instance
                                logger.info(f"Successfully loaded tool: {tool_name} from {module_path}")
                except Exception as e:
                    logger.error(f"Failed to load plugin from {module_name}.py: {e}", exc_info=True)

    def get_tool(self, name: str) -> BaseTool:
        return self.tools.get(name)

    def get_all_tools(self) -> dict:
        """Returns a dictionary of all loaded tools with their details."""
        tool_details = {}
        for name, instance in self.tools.items():
            tool_details[name] = {
                "description": instance.get_description(),
                "config_spec": instance.get_config_spec(),
                "name": instance.get_name() # Ensure name is part of the details
            }
        return tool_details

    def execute_tool(self, name: str, params: dict) -> dict:
        tool = self.get_tool(name)
        if not tool:
            logger.error(f"Attempted to execute non-existent tool: {name}")
            return {"success": False, "error": f"Tool '{name}' not found."}

        # Validate params against tool's config_spec (basic validation)
        config_spec = tool.get_config_spec()
        validated_params = {}
        for param_name, spec in config_spec.items():
            if spec.get("required") and param_name not in params:
                return {"success": False, "error": f"Missing required parameter '{param_name}' for tool '{name}'."}

            value = params.get(param_name, spec.get("default"))

            # Basic type checking (can be expanded)
            param_type = spec.get("type")
            if value is not None: # Only check type if value is provided or has a default
                if param_type == "integer" and not isinstance(value, int):
                    try:
                        value = int(value)
                    except ValueError:
                        return {"success": False, "error": f"Parameter '{param_name}' must be an integer."}
                elif param_type == "string" and not isinstance(value, str):
                    try:
                        value = str(value)
                    except ValueError:
                         return {"success": False, "error": f"Parameter '{param_name}' must be a string."}
                elif param_type == "boolean" and not isinstance(value, bool):
                    if isinstance(value, str):
                        value = value.lower() == 'true'
                    else:
                        return {"success": False, "error": f"Parameter '{param_name}' must be a boolean (true/false)."}

            validated_params[param_name] = value

        logger.info(f"Executing tool '{name}' with params: {validated_params}")
        try:
            return tool.execute(validated_params)
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}", exc_info=True)
            return {"success": False, "error": f"An unexpected error occurred while executing {name}: {str(e)}"}
