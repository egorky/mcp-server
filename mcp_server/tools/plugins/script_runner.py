import subprocess
import logging
from mcp_server.tools.base_tool import BaseTool
import os

logger = logging.getLogger(__name__)

class ScriptRunnerTool(BaseTool):

    @staticmethod
    def get_name() -> str:
        return "script_runner"

    def get_description(self) -> str:
        return "Executes a shell script and returns its output. Configure 'scripts_base_path' in general tool config."

    def get_config_spec(self) -> dict:
        return {
            "script_name": {"type": "string", "required": True, "description": "Name of the script file to execute (e.g., 'my_script.sh')."},
            "arguments": {"type": "string", "required": False, "default": "", "description": "Space-separated arguments for the script."},
            "working_directory": {"type": "string", "required": False, "description": "Optional working directory for the script. Defaults to script's location."}
        }

    def execute(self, params: dict) -> dict:
        script_name = params.get("script_name")
        arguments = params.get("arguments", "").split() # Split string into list of args

        scripts_base_path = self.config.get("scripts_base_path", "/mcp_scripts") # Configurable base path
        if not os.path.isabs(scripts_base_path):
             # If not absolute, consider it relative to some project root or make it mandatory absolute
            logger.warning(f"scripts_base_path '{scripts_base_path}' is not absolute. This might lead to issues.")
            # For now, we'll proceed, but this should be documented or enforced.

        script_full_path = os.path.join(scripts_base_path, script_name)

        if not os.path.exists(script_full_path):
            logger.error(f"Script file not found: {script_full_path}")
            return {"success": False, "error": f"Script file not found: {script_full_path}"}

        if not os.access(script_full_path, os.X_OK):
            logger.error(f"Script file is not executable: {script_full_path}")
            return {"success": False, "error": f"Script file is not executable: {script_full_path}. Please use chmod +x."}

        working_dir = params.get("working_directory")
        if working_dir:
            if not os.path.isdir(working_dir):
                logger.error(f"Specified working directory does not exist: {working_dir}")
                return {"success": False, "error": f"Working directory not found: {working_dir}"}
        else:
            working_dir = os.path.dirname(script_full_path)


        command = [script_full_path] + arguments
        logger.info(f"Executing script: {' '.join(command)} in {working_dir}")

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=working_dir
            )
            stdout, stderr = process.communicate(timeout=self.config.get("default_timeout", 60)) # Configurable timeout

            if process.returncode == 0:
                logger.info(f"Script {script_name} executed successfully.")
                return {"success": True, "data": {"stdout": stdout, "stderr": stderr, "return_code": process.returncode}}
            else:
                logger.error(f"Script {script_name} failed with return code {process.returncode}. Stderr: {stderr}")
                return {"success": False, "error": stderr, "data": {"stdout": stdout, "return_code": process.returncode}}
        except subprocess.TimeoutExpired:
            logger.error(f"Script {script_name} timed out.")
            process.kill()
            stdout, stderr = process.communicate()
            return {"success": False, "error": "Script execution timed out.", "data": {"stdout": stdout, "stderr": stderr}}
        except Exception as e:
            logger.error(f"Error executing script {script_name}: {e}", exc_info=True)
            return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}
