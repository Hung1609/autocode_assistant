# các tool's name phải hợp với địa chỉ API

def get_tool_definitions():
    return [
        {
            "name": "create_file",
            "description": "Creates a new file at the specified path relative to the project workspace, with the given content. Use this when asked to create a new file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path within the project workspace where the file should be created. e.g., 'src/components/Button.js' or 'docs/README.md'"
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content to write into the new file."
                    }
                },
                "required": ["path", "content"]
            }
        },
        {
            "name": "read_file",
            "description": "Reads and returns the entire content of a file at the specified relative path within the project workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path (within the project workspace) of the file to read. e.g., 'package.json' or 'src/main.py'"
                    }
                },
                "required": ["path"]
            }
        },
        {
            "name": "list_files",
            "description": "Lists all files and directories directly within the specified relative path within the project workspace. If no path is provided, lists the root of the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Optional. The relative path (within the project workspace) of the directory to list. Defaults to the workspace root if omitted. e.g., 'src' or 'assets/images'"
                    }
                },
            }
        },
        {
            "name": "create_directory",
            "description": "Creates a new directory (including any necessary parent directories) at the specified relative path within the project workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path (within the project workspace) where the directory should be created. e.g., 'src/utils' or 'tests/data'"
                    }
                },
                "required": ["path"]
            }
        },
        {
            "name": "edit_file",
            "description": "Edits an existing file at the specified relative path within the project workspace. Currently, this replaces the *entire* content of the file with the provided text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path (within the project workspace) of the file to edit. e.g., 'config.py' or 'styles/main.css'"
                    },
                    "changes_description": {
                        "type": "string",
                        "description": "The new, complete content that should overwrite the existing file content."
                    }
                },
                "required": ["path", "changes_description"]
            }
        }
    ]