# các tool's name phải hợp với địa chỉ API

def get_tool_definitions():
    return [
        {
            "name": "create_file",
            "description": "Creates a new file at the specified path relative to the project workspace, with the given content. Use this when asked to create a new file.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "path": {
                        "type": "STRING",
                        "description": "The relative path within the project workspace where the file should be created. e.g., 'src/components/Button.js' or 'docs/README.md'"
                    },
                    "content": {
                        "type": "STRING",
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
                "type": "OBJECT",
                "properties": {
                    "path": {
                        "type": "STRING",
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
                "type": "OBJECT",
                "properties": {
                    "path": {
                        "type": "STRING",
                        "description": "Optional. The relative path (within the project workspace) of the directory to list. Defaults to the workspace root if omitted. e.g., 'src' or 'assets/images'"
                    }
                },
            }
        },
        {
            "name": "create_directory",
            "description": "Creates a new directory (including any necessary parent directories) at the specified relative path within the project workspace.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "path": {
                        "type": "STRING",
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
                "type": "OBJECT",
                "properties": {
                    "path": {
                        "type": "STRING",
                        "description": "The relative path (within the project workspace) of the file to edit. e.g., 'config.py' or 'styles/main.css'"
                    },
                    "changes_description": {
                        "type": "STRING",
                        "description": "The new, complete content that should overwrite the existing file content."
                    }
                },
                "required": ["path", "changes_description"]
            }
        },
        {
            "name": "generate_specification_json",
            "description": "Use this tool ONLY when the user provides a textual description or requirements for a NEW software project and asks to generate the initial SPECIFICATION document. Takes the user's text description as input and generates a JSON specification file (ending in .spec.json). Returns the relative path to the created specification file.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "project_description": { 
                        "type": "STRING",    
                        "description": "The user's detailed natural language description of the software requirements, purpose, scope, features, etc. This description MUST be extracted directly from the user's prompt or recent messages." # Refined description
                    },
                    "output_filename_base": {
                         "type": "STRING",
                         "description": "Optional. A base name (like 'my_project' or 'todo_app') to use for the output filename, often derived from the project description or user's request. If omitted, a default name will be generated."
                     }
                },
                "required": ["project_description"] 
            }
        },
        {
            "name": "generate_design_json",
            "description": "Use this tool ONLY when the user provides the path to an EXISTING specification JSON file (usually ending in .spec.json) and asks to generate the technical DESIGN document based on it. Takes the path to the specification file as input and generates a JSON design file (ending in .design.json). Returns the relative path to the created design file.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "spec_file_path": {
                        "type": "STRING",
                        "description": "The relative path (within the project workspace) to the existing '.spec.json' file to be used as input for generating the design."
                    },
                    "output_filename_base": {
                        "type": "STRING",
                        "description": "Optional. A base name (like 'my_project' or 'todo_app') to use for the output file. If omitted, a default name based on project description or 'specification' will be used."
                    }
                },
                "required": ["spec_file_path"]
            }
        }
    ]