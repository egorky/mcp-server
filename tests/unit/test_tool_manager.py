import pytest
from mcp_server.tool_manager import ToolManager
from mcp_server.tools.base_tool import BaseTool
import os

# A simple mock tool for testing
class MockTool(BaseTool):
    def __init__(self, config=None):
        super().__init__(config)
        self.executed_params = None

    @staticmethod
    def get_name(): return "mock_tool"
    def get_description(self): return "A mock tool for testing."
    def get_config_spec(self):
        return {"param1": {"type": "string", "required": True}}
    def execute(self, params):
        self.executed_params = params
        if params.get("param1") == "fail":
            return {"success": False, "error": "Mock tool failed as requested"}
        return {"success": True, "data": "Mock tool executed with " + str(params)}

@pytest.fixture
def mock_plugin_dir(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    # Create a mock plugin file
    mock_plugin_content = """
from mcp_server.tools.base_tool import BaseTool
class MyTestableTool(BaseTool):
    @staticmethod
    def get_name(): return "my_testable_tool"
    def get_description(self): return "Testable tool description."
    def get_config_spec(self): return {"test_param": {"type": "integer", "required": False, "default": 10}}
    def execute(self, params): return {"success": True, "data": params.get("test_param", 0) * 2}
"""
    (plugins_dir / "my_plugin.py").write_text(mock_plugin_content)
    return str(plugins_dir)


def test_tool_discovery(mock_plugin_dir, app_config):
    # app_config provides tool-specific configs if needed
    tm = ToolManager(plugin_dir=mock_plugin_dir, global_config=app_config)
    assert "my_testable_tool" in tm.get_all_tools()
    tool_info = tm.get_all_tools()["my_testable_tool"]
    assert tool_info["description"] == "Testable tool description."

def test_get_tool(mock_plugin_dir, app_config):
    tm = ToolManager(plugin_dir=mock_plugin_dir, global_config=app_config)
    tool_instance = tm.get_tool("my_testable_tool")
    assert tool_instance is not None
    assert tool_instance.get_name() == "my_testable_tool"
    assert tm.get_tool("non_existent_tool") is None

def test_execute_tool_success(mock_plugin_dir, app_config):
    tm = ToolManager(plugin_dir=mock_plugin_dir, global_config=app_config)
    result = tm.execute_tool("my_testable_tool", {"test_param": 5})
    assert result["success"] is True
    assert result["data"] == 10 # 5 * 2

    # Test with default param
    result_default = tm.execute_tool("my_testable_tool", {})
    assert result_default["success"] is True
    assert result_default["data"] == 20 # 10 * 2 (default)


def test_execute_tool_param_validation_missing_required(app_config):
    # Use internal MockTool directly for this, no discovery needed
    tm = ToolManager(plugin_dir="non_existent_dir_for_this_test", global_config=app_config)
    tm.tools["mock_tool"] = MockTool() # Manually add our internal mock tool

    result = tm.execute_tool("mock_tool", {}) # param1 is required
    assert result["success"] is False
    assert "Missing required parameter 'param1'" in result["error"]

def test_execute_tool_param_validation_wrong_type(app_config, mock_plugin_dir):
    tm = ToolManager(plugin_dir=mock_plugin_dir, global_config=app_config)
    # my_testable_tool expects 'test_param' as integer
    result = tm.execute_tool("my_testable_tool", {"test_param": "not_an_int"})
    assert result["success"] is False
    assert "Parameter 'test_param' must be an integer" in result["error"]


def test_tool_config_passed_to_tool(tmp_path, app_config):
    plugins_dir = tmp_path / "plugins_cfg_test"
    plugins_dir.mkdir()
    tool_config_content = """
from mcp_server.tools.base_tool import BaseTool
class ConfigurableTool(BaseTool):
    @staticmethod
    def get_name(): return "configurable_tool"
    def get_description(self): return "Tests tool config."
    def get_config_spec(self): return {}
    def execute(self, params): return {"success": True, "tool_config_value": self.config.get("my_key")}
"""
    (plugins_dir / "configurable_plugin.py").write_text(tool_config_content)

    # Add tool-specific config to app_config
    test_specific_app_config = app_config.copy()
    test_specific_app_config['tools'] = {
        "configurable_tool": {"my_key": "my_value"}
    }

    tm = ToolManager(plugin_dir=str(plugins_dir), global_config=test_specific_app_config)
    assert "configurable_tool" in tm.tools

    result = tm.execute_tool("configurable_tool", {})
    assert result["success"]
    assert result["tool_config_value"] == "my_value"
