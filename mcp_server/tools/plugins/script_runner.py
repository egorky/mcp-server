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
        return "Executes a shell script and returns its output. Configure 'scripts_base_path' and 'default_timeout' in tool config. Timeout can be overridden per execution."

    def get_config_spec(self) -> dict:
        return {
            "script_name": {"type": "string", "required": True, "description": "Name of the script file to execute (e.g., 'my_script.sh')."},
            "arguments": {"type": "string", "required": False, "default": "", "description": "Space-separated arguments for the script."},
            "working_directory": {"type": "string", "required": False, "description": "Optional working directory for the script. Defaults to script's location."},
            "timeout": {"type": "integer", "required": False, "description": "Optional execution timeout in seconds for this specific run. Overrides tool's default_timeout."}
        }

    def execute(self, params: dict) -> dict:
        script_name = params.get("script_name")
        arguments_str = params.get("arguments", "")
        # Ensure arguments are handled as a list of strings for Popen
        arguments = arguments_str.split() if arguments_str else []


        scripts_base_path = self.config.get("scripts_base_path", "/mcp_scripts")
        if not os.path.isabs(scripts_base_path):
            logger.warning(f"scripts_base_path '{scripts_base_path}' is not absolute. This might lead to issues. Recommended to use an absolute path in configuration.")
            # For robustness in testing or certain environments, one might resolve it:
            # scripts_base_path = os.path.abspath(scripts_base_path)


        script_full_path = os.path.join(scripts_base_path, script_name)

        if not os.path.exists(script_full_path):
            logger.error(f"Script file not found: {script_full_path}")
            return {"success": False, "error": f"Script file not found: {script_full_path}"}

        if not os.access(script_full_path, os.X_OK):
            logger.error(f"Script file is not executable: {script_full_path}")
            return {"success": False, "error": f"Script file is not executable: {script_full_path}. Please use chmod +x."}

        working_dir_param = params.get("working_directory")
        final_working_dir = None
        if working_dir_param:
            if not os.path.isdir(working_dir_param):
                logger.error(f"Specified working directory does not exist: {working_dir_param}")
                return {"success": False, "error": f"Working directory not found: {working_dir_param}"}
            final_working_dir = working_dir_param
        else:
            final_working_dir = os.path.dirname(script_full_path) # Default to script's directory

        # Determine timeout: use parameter if provided, else tool's default config, else a fallback.
        execution_timeout_param = params.get("timeout")
        if execution_timeout_param is not None:
            try:
                current_timeout = int(execution_timeout_param)
                logger.debug(f"Using per-execution timeout for script '{script_name}': {current_timeout}s.")
            except ValueError:
                logger.warning(f"Invalid 'timeout' parameter for script '{script_name}': '{execution_timeout_param}'. Using default.")
                current_timeout = self.config.get("default_timeout", 60) # Default from tool config or hardcoded 60s
        else:
            current_timeout = self.config.get("default_timeout", 60) # Default from tool config or hardcoded 60s
            logger.debug(f"Using default timeout for script '{script_name}': {current_timeout}s.")


        command = [script_full_path] + arguments
        logger.info(f"Executing script: {' '.join(command)} in '{final_working_dir}' with timeout {current_timeout}s")

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, # Decodes stdout/stderr as text
                cwd=final_working_dir # Set working directory
            )
            stdout, stderr = process.communicate(timeout=current_timeout)

            if process.returncode == 0:
                logger.info(f"Script {script_name} executed successfully.")
                return {"success": True, "data": {"stdout": stdout, "stderr": stderr, "return_code": process.returncode}}
            else:
                logger.warning(f"Script {script_name} failed with return code {process.returncode}. Stdout: '{stdout[:200]}...', Stderr: '{stderr[:200]}...'")
                return {"success": False, "error": stderr, "data": {"stdout": stdout, "return_code": process.returncode}}
        except subprocess.TimeoutExpired:
            logger.error(f"Script {script_name} timed out after {current_timeout} seconds.")
            # Ensure process is terminated
            process.kill() # Send SIGKILL
            # Try to communicate again to get any final output after kill (might be empty)
            stdout_after_kill, stderr_after_kill = process.communicate()
            logger.debug(f"Script {script_name} killed due to timeout. stdout after kill: '{stdout_after_kill[:200]}...', stderr after kill: '{stderr_after_kill[:200]}...'")
            return {"success": False, "error": "Script execution timed out.", "data": {"stdout": stdout_after_kill, "stderr": stderr_after_kill, "details": f"Process killed after {current_timeout}s timeout."}}
        except FileNotFoundError as e: # Should be caught by os.path.exists, but as a safeguard for Popen itself
            logger.error(f"Script file '{script_full_path}' not found during Popen: {e}", exc_info=True)
            return {"success": False, "error": f"Script file not found: {script_full_path}. Ensure it exists and path is correct."}
        except Exception as e:
            logger.error(f"Error executing script {script_name}: {e}", exc_info=True)
            return {"success": False, "error": f"An unexpected error occurred while executing script: {str(e)}"}
