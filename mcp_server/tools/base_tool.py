from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseTool(ABC):
    def __init__(self, config=None):
        """
        Initializes the tool with its specific configuration.
        'config' is the section of the global config relevant to this tool.
        """
        self.config = config if config else {}
        self.name = self.get_name()
        logger.info(f"Initialized tool: {self.name} with config: {self.config}")

    @abstractmethod
    def get_name(self) -> str:
        """Returns the unique name of the tool."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Returns a brief description of what the tool does."""
        pass

    @abstractmethod
    def get_config_spec(self) -> dict:
        """
        Returns a specification of the configuration parameters this tool accepts during execution.
        Example:
        {
            "param_name": {
                "type": "string", "required": True, "default": "value",
                "description": "Human-readable description"
            },
            "another_param": {"type": "integer", "required": False}
        }
        This helps in validating input and generating UI forms.
        """
        pass

    @abstractmethod
    def execute(self, params: dict) -> dict:
        """
        Executes the tool with the given parameters.
        'params' is a dictionary containing validated parameters based on get_config_spec.
        Returns a dictionary with the execution result, including 'success' (boolean)
        and 'data' or 'error'.
        """
        pass
