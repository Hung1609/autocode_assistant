import os
import logging
import subprocess
import sys
from pydantic import BaseModel, Field
from langchain.tools import Tool

def list_directory_contents(directory: str) -> str:
    logging.info(f"Tool 'list_directory_contents' called with directory: {directory}")
    if not isinstance(directory, str) or not directory:
        logging.error("Invalid directory path provided.")
        return "Error: Directory path must be a non-empty string."
   
    try:
        if not os.path.exists(directory):
            logging.error(f"Directory does not exist: {directory}")
            return f"Error: Directory '{directory}' does not exist."

        if not os.path.isdir(directory):
            logging.error(f"Path is not a directory: {directory}")
            return f"Error: Path '{directory}' is not a directory."
        
        contents = os.listdir(directory)
        if not contents:
            logging.info(f"Directory is empty: {directory}")
            return f"Directory '{directory}' is empty."
        else:
            logging.info(f"Successfully listed contents for: {directory}")
            return f"Contents of '{directory}':\n" + "\n".join(contents)
    
    except PermissionError:
        logging.error(f"Permission denied for directory: {directory}")
        return f"Error: Permission denied for directory '{directory}'."
    except Exception as e:
        logging.exception(f"An unexpected error occurred while listing directory {directory}: {e}")
        return f"Error: An unexpected error occurred: {e}"

def read_file_contents(file_path: str) -> str:
    logging.info(f"Tool 'read_file_contents' called with file path: {file_path}")
    if not isinstance(file_path, str) or not file_path:
        logging.error("Invalid file path provided.")
        return "Error: File path must be a non-empty string."
    
    try:
        if not os.path.exists(file_path):
            logging.error(f"File does not exist: {file_path}")
            return f"Error: File '{file_path}' does not exist."
        
        if not os.path.isfile(file_path):
            logging.error(f"Path is not a file: {file_path}")
            return f"Error: Path '{file_path}' is not a file."
        
        with open(file_path, 'r') as file:
            contents = file.read()
            logging.info(f"Successfully read contents for: {file_path}")
            return f"Contents of '{file_path}':\n{contents}"
    
    except PermissionError:
        logging.error(f"Permission denied for file: {file_path}")
        return f"Error: Permission denied for file '{file_path}'."
    except Exception as e:
        logging.exception(f"An unexpected error occurred while reading file {file_path}: {e}")
        return f"Error: An unexpected error occurred: {e}"


def write_to_file(tool_input: dict) -> str:
    # Validate and extract arguments from the input dictionary
    if not isinstance(tool_input, dict):
        logging.error(f"Invalid input type for write_to_file: Expected dict, got {type(tool_input)}")
        return "Error: Invalid input type for write_to_file tool."

    file_path = tool_input.get('file_path')
    content = tool_input.get('content') # Use .get() for safer access

    logging.info(f"Tool 'write_to_file' called with file_path: {file_path}") # Content logging removed for brevity/security

    if not file_path or not isinstance(file_path, str):
         logging.error("Invalid input: 'file_path' missing or not a string in tool_input.")
         return "Error: 'file_path' missing or invalid in tool input."
    # Allow content to be None or empty string, handle appropriately
    if content is None:
         content = "" # Default to empty string if content is missing
         logging.warning("Input 'content' was missing, defaulting to empty string.")
    elif not isinstance(content, str):
         content = str(content) # Attempt to convert if not string
         logging.warning(f"Input 'content' was not a string ({type(content)}), converted to string.") 

    try:
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
            logging.info(f"Ensured parent directory exists: {parent_dir}")

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
            logging.info(f"Successfully wrote to file: {file_path}")
            return f"Successfully wrote to '{file_path}'."
    
    except PermissionError:
        logging.error(f"Permission denied for file: {file_path}")
        return f"Error: Permission denied for file '{file_path}'."
    except Exception as e:
        logging.exception(f"An unexpected error occurred while writing to file {file_path}: {e}")
        return f"Error: An unexpected error occurred: {e}"

def execute_shell_command(command: str) -> str:
    logging.info(f"Tool 'execute_shell_command' called with command: {command}")
    if not isinstance(command, str) or not command:
        logging.error("Invalid input: Command must be a non-empty string.")
        return "Error: Command must be a non-empty string."

    try:
        is_windows = sys.platform.startswith("win")
        shell_executable = "cmd.exe" if is_windows else "/bin/sh" # shell selection

        timeout = 60 # prevent hanging commands
        result = subprocess.run(
                command,
                shell=True, # DANGER
                capture_output=True,
                timeout=timeout,
                check=False
        )

        output = f"Command: {command}\nExit code: {result.returncode}\n"
        if result.stdout:
            output += f"--- stdout ---\n{result.stdout.strip()}\n"
        if result.stderr:
            output += f"--- stderr ---\n{result.stderr.strip()}\n"

        logging.info(f"Command executed. Exit code: {result.returncode}")
        return output.strip()

    except subprocess.TimeoutExpired:
        logging.error(f"Command timed out after {timeout} seconds: {command}")
        return f"Error: Command timed out after {timeout} seconds."
    except Exception as e:
        logging.exception(f"An unexpected error occurred while executing command '{command}': {e}")
        return f"Error: An unexpected error occurred while executing command: {e}"

class WriteFileInput(BaseModel):
    file_path: str = Field(description="The path of the file to write to.")
    content: str = Field(description="The content to write into the file.")

list_directory_tool = Tool(
    name="list_directory",
    func=list_directory_contents,
    description="Useful for listing the files and folders within a specified directory path. Input should be a valid directory path string.",
)

read_file_tool = Tool(
    name="read_file",
    func=read_file_contents,
    description="Useful for reading the content of a specified file path. Input should be a valid file path string.",
)

write_file_tool = Tool(
    name="write_file",
    func=write_to_file,
    description="Useful for writing content to a specified file path. Creates the file if it doesn't exist, overwrites it if it does. Input requires 'file_path' (string) and 'content' (string).",
    # If the LLM struggles with providing both args, consider using args_schema with Pydantic
)

execute_command_tool = Tool(
    name="execute_command",
    func=execute_shell_command,
    description="Useful for executing a shell command in the terminal. Input should be a valid command string. Use with extreme caution.",
)
# --- Add more tool definitions below ---

all_tools = [list_directory_tool, read_file_tool, write_file_tool, execute_command_tool]

logging.info(f"All tools defined: {[tool.name for tool in all_tools]}")