#!/usr/bin/env python3
"""
Autonomous Code Generation System - Code Generator
-------------------------------------------------
This script handles:
1. Code generation based on JSON specifications
2. Test creation for the generated code
3. Automated bug fixing
"""

import os
import json
import argparse
import logging
from typing import Dict, List, Any, Optional, Tuple


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CodeGenerator:
    """Generates code based on JSON specifications."""
    
    def __init__(self, specification_file: str, output_dir: str, prompts_dir: str = "prompts"):
        """
        Initialize the CodeGenerator.
        
        Args:
            specification_file: Path to the JSON specification file
            output_dir: Directory where generated code will be saved
            prompts_dir: Directory containing prompt files
        """
        self.specification_file = specification_file
        self.output_dir = output_dir
        self.prompts_dir = prompts_dir
        self.specification = self._load_specification()
        
    def _load_specification(self) -> Dict[str, Any]:
        """
        Load the JSON specification from file.
        
        Returns:
            Dictionary containing the JSON specification
        """
        try:
            with open(self.specification_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logger.error(f"Specification file {self.specification_file} not found")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in specification file {self.specification_file}")
            return {}
    
    def determine_project_structure(self) -> Dict[str, Any]:
        """
        Determine the project structure based on the specification.
        
        Returns:
            Dictionary containing the project structure
        """
        logger.info("Determining project structure...")
        
        # In a real implementation, this would use an LLM to analyze the specification
        # and determine the appropriate project structure
        
        # Placeholder for project structure
        project_structure = {
            "language": "python",  # Could be determined based on requirements
            "framework": "flask",  # Could be determined based on requirements
            "directories": [
                {"path": "src", "description": "Source code"},
                {"path": "src/models", "description": "Data models"},
                {"path": "src/controllers", "description": "Business logic"},
                {"path": "src/views", "description": "User interface"},
                {"path": "src/utils", "description": "Utility functions"},
                {"path": "tests", "description": "Test cases"},
                {"path": "docs", "description": "Documentation"}
            ],
            "files": [
                {"path": "src/__init__.py", "description": "Package initialization"},
                {"path": "src/app.py", "description": "Application entry point"},
                {"path": "src/config.py", "description": "Configuration settings"},
                {"path": "src/models/__init__.py", "description": "Models package initialization"},
                {"path": "src/controllers/__init__.py", "description": "Controllers package initialization"},
                {"path": "src/views/__init__.py", "description": "Views package initialization"},
                {"path": "src/utils/__init__.py", "description": "Utils package initialization"},
                {"path": "tests/__init__.py", "description": "Tests package initialization"},
                {"path": "requirements.txt", "description": "Project dependencies"},
                {"path": "README.md", "description": "Project documentation"}
            ]
        }
        
        # Add files based on data model
        if "dataModel" in self.specification and "entities" in self.specification["dataModel"]:
            for entity in self.specification["dataModel"]["entities"]:
                entity_name = entity["name"].lower()
                project_structure["files"].append({
                    "path": f"src/models/{entity_name}.py",
                    "description": f"{entity['name']} model"
                })
                project_structure["files"].append({
                    "path": f"src/controllers/{entity_name}_controller.py",
                    "description": f"{entity['name']} controller"
                })
                project_structure["files"].append({
                    "path": f"tests/test_{entity_name}.py",
                    "description": f"{entity['name']} tests"
                })
        
        return project_structure
    
    def create_project_structure(self, project_structure: Dict[str, Any]) -> None:
        logger.info("Creating project directory structure...")
        
        # Create directories
        for directory in project_structure["directories"]:
            dir_path = os.path.join(self.output_dir, directory["path"])
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")
        
        # Create empty files
        for file in project_structure["files"]:
            file_path = os.path.join(self.output_dir, file["path"])
            # Ensure the directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            # Create an empty file
            with open(file_path, 'w', encoding='utf-8') as f:
                pass
            logger.info(f"Created file: {file_path}")
    
    def generate_code_for_file(self, file_path: str, project_structure: Dict[str, Any]) -> str:
        """
        Generate code for a specific file.
        
        Args:
            file_path: Path to the file
            project_structure: Dictionary containing the project structure
            
        Returns:
            Generated code as a string
        """
        logger.info(f"Generating code for file: {file_path}")
        
        # In a real implementation, this would use an LLM to generate code
        # based on the specification and file type
        
        # Placeholder for generated code
        if file_path.endswith("app.py"):
            return self._generate_app_code()
        elif file_path.endswith("config.py"):
            return self._generate_config_code()
        elif "/models/" in file_path and not file_path.endswith("__init__.py"):
            return self._generate_model_code(os.path.basename(file_path).replace(".py", ""))
        elif "/controllers/" in file_path and not file_path.endswith("__init__.py"):
            return self._generate_controller_code(os.path.basename(file_path).replace("_controller.py", ""))
        elif file_path.endswith("README.md"):
            return self._generate_readme()
        elif file_path.endswith("requirements.txt"):
            return self._generate_requirements()
        elif file_path.endswith("__init__.py"):
            return "# Package initialization\n"
        else:
            return f"# TODO: Generate code for {file_path}\n"
    
    def _generate_app_code(self) -> str:
        """Generate code for the main application file."""
        return """#!/usr/bin/env python3
\"\"\"
Main application entry point.
\"\"\"

from flask import Flask
from src.config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Import and register blueprints
# TODO: Import and register blueprints for each controller

@app.route('/')
def index():
    \"\"\"Home page route.\"\"\"
    return "Welcome to the application!"

if __name__ == '__main__':
    app.run(debug=True)
"""
    
    def _generate_config_code(self) -> str:
        """Generate code for the configuration file."""
        return """#!/usr/bin/env python3
\"\"\"
Application configuration.
\"\"\"

import os

class Config:
    \"\"\"Configuration settings.\"\"\"
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    DEBUG = os.environ.get('DEBUG') or True
    
    # Database settings
    DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///app.db'
    
    # Application settings
    APP_NAME = 'Generated Application'
    APP_VERSION = '0.1.0'
"""
    
    def _generate_model_code(self, entity_name: str) -> str:
        """Generate code for a model file."""
        # Find the entity in the specification
        entity = None
        if "dataModel" in self.specification and "entities" in self.specification["dataModel"]:
            for e in self.specification["dataModel"]["entities"]:
                if e["name"].lower() == entity_name:
                    entity = e
                    break
        
        if not entity:
            return f"# Model for {entity_name}\n# TODO: Implement model\n"
        
        # Generate model code based on entity specification
        code = f"""#!/usr/bin/env python3
\"\"\"
{entity['name']} model.
\"\"\"

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class {entity['name']}:
    \"\"\"
    {entity.get('description', f'{entity["name"]} model')}
    \"\"\"
"""
        
        # Add attributes
        if "attributes" in entity:
            for attr in entity["attributes"]:
                attr_type = self._map_attribute_type(attr["type"])
                is_required = attr.get("isRequired", False)
                
                if is_required:
                    code += f"    {attr['name']}: {attr_type}\n"
                else:
                    code += f"    {attr['name']}: Optional[{attr_type}] = None\n"
        
        # Add relationships
        if "relationships" in entity:
            for rel in entity["relationships"]:
                rel_type = rel["type"]
                related_entity = rel["relatedEntity"]
                
                if rel_type == "one-to-many":
                    code += f"    {related_entity.lower()}_list: List['{related_entity}'] = None\n"
                elif rel_type == "many-to-one":
                    code += f"    {related_entity.lower()}: Optional['{related_entity}'] = None\n"
                elif rel_type == "many-to-many":
                    code += f"    {related_entity.lower()}_list: List['{related_entity}'] = None\n"
                else:  # one-to-one
                    code += f"    {related_entity.lower()}: Optional['{related_entity}'] = None\n"
        
        # Add created_at and updated_at fields
        code += "    created_at: datetime = datetime.now()\n"
        code += "    updated_at: datetime = datetime.now()\n"
        
        # Add string representation
        code += "\n    def __str__(self) -> str:\n"
        code += f"        return f\"{entity['name']}(id={{self.id}})\"\n"
        
        return code
    
    def _map_attribute_type(self, attr_type: str) -> str:
        """Map attribute type to Python type."""
        type_mapping = {
            "string": "str",
            "integer": "int",
            "float": "float",
            "boolean": "bool",
            "date": "datetime.date",
            "datetime": "datetime",
            "array": "List",
            "object": "dict"
        }
        
        return type_mapping.get(attr_type.lower(), "str")
    
    def _generate_controller_code(self, entity_name: str) -> str:
        """Generate code for a controller file."""
        entity_class = entity_name.capitalize()
        
        return f"""#!/usr/bin/env python3
\"\"\"
Controller for {entity_class} operations.
\"\"\"

from flask import Blueprint, request, jsonify
from src.models.{entity_name} import {entity_class}

# Create blueprint
{entity_name}_bp = Blueprint('{entity_name}', __name__, url_prefix='/{entity_name}s')

@{entity_name}_bp.route('/', methods=['GET'])
def get_all_{entity_name}s():
    \"\"\"Get all {entity_name}s.\"\"\"
    # TODO: Implement database query
    return jsonify({"message": "Get all {entity_name}s"})

@{entity_name}_bp.route('/<int:id>', methods=['GET'])
def get_{entity_name}(id):
    \"\"\"Get a specific {entity_name}.\"\"\"
    # TODO: Implement database query
    return jsonify({"message": f"Get {entity_name} {{id}}"})

@{entity_name}_bp.route('/', methods=['POST'])
def create_{entity_name}():
    \"\"\"Create a new {entity_name}.\"\"\"
    # TODO: Implement database insert
    data = request.get_json()
    return jsonify({"message": "Created {entity_name}", "data": data})

@{entity_name}_bp.route('/<int:id>', methods=['PUT'])
def update_{entity_name}(id):
    \"\"\"Update a specific {entity_name}.\"\"\"
    # TODO: Implement database update
    data = request.get_json()
    return jsonify({"message": f"Updated {entity_name} {{id}}", "data": data})

@{entity_name}_bp.route('/<int:id>', methods=['DELETE'])
def delete_{entity_name}(id):
    \"\"\"Delete a specific {entity_name}.\"\"\"
    # TODO: Implement database delete
    return jsonify({"message": f"Deleted {entity_name} {{id}}"})
"""
    
    def _generate_readme(self) -> str:
        """Generate README.md content."""
        project_name = self.specification.get("metadata", {}).get("projectName", "Generated Project")
        purpose = self.specification.get("systemOverview", {}).get("purpose", "A generated application")
        
        return f"""# {project_name}

## Overview
{purpose}

## Features
"""
    
    def _generate_requirements(self) -> str:
        """Generate requirements.txt content."""
        # In a real implementation, this would be determined based on the specification
        return """flask==2.0.1
pytest==6.2.5
"""
    
    def write_generated_code(self, file_path: str, code: str) -> None:
        """
        Write generated code to a file.
        
        Args:
            file_path: Path to the file
            code: Generated code
        """
        full_path = os.path.join(self.output_dir, file_path)
        with open(full_path, 'w', encoding='utf-8') as file:
            file.write(code)
        logger.info(f"Wrote code to file: {full_path}")
    
    def generate_code(self) -> None:
        """Generate code based on the specification."""
        logger.info("Starting code generation...")
        
        # Determine project structure
        project_structure = self.determine_project_structure()
        
        # Create project structure
        self.create_project_structure(project_structure)
        
        # Generate code for each file
        for file in project_structure["files"]:
            file_path = file["path"]
            code = self.generate_code_for_file(file_path, project_structure)
            self.write_generated_code(file_path, code)
        
        logger.info("Code generation completed")


class TestGenerator:
    """Generates tests for the generated code."""
    
    def __init__(self, specification_file: str, code_dir: str, output_dir: str):
        """
        Initialize the TestGenerator.
        
        Args:
            specification_file: Path to the JSON specification file
            code_dir: Directory containing the generated code
            output_dir: Directory where generated tests will be saved
        """
        self.specification_file = specification_file
        self.code_dir = code_dir
        self.output_dir = output_dir
        self.specification = self._load_specification()
    
    def _load_specification(self) -> Dict[str, Any]:
        """
        Load the JSON specification from file.
        
        Returns:
            Dictionary containing the JSON specification
        """
        try:
            with open(self.specification_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logger.error(f"Specification file {self.specification_file} not found")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in specification file {self.specification_file}")
            return {}
    
    def generate_tests(self) -> None:
        """Generate tests for the generated code."""
        logger.info("Starting test generation...")
        
        # In a real implementation, this would analyze the generated code
        # and create appropriate tests based on the specification
        
        # Create test directory if it doesn't exist
        os.makedirs(os.path.join(self.output_dir, "tests"), exist_ok=True)
        
        # Generate test files
        self._generate_model_tests()
        self._generate_controller_tests()
        self._generate_integration_tests()
        
        logger.info("Test generation completed")
    
    def _generate_model_tests(self) -> None:
        """Generate tests for models."""
        if "dataModel" not in self.specification or "entities" not in self.specification["dataModel"]:
            return
        
        for entity in self.specification["dataModel"]["entities"]:
            entity_name = entity["name"].lower()
            test_file = os.path.join(self.output_dir, f"tests/test_{entity_name}_model.py")
            
            with open(test_file, 'w', encoding='utf-8') as file:
                file.write(f"""#!/usr/bin/env python3
\"\"\"
Tests for {entity['name']} model.
\"\"\"

import pytest
from datetime import datetime
from src.models.{entity_name} import {entity['name']}

def test_{entity_name}_creation():
    \"\"\"Test {entity_name} creation.\"\"\"
    # TODO: Implement test
    {entity_name} = {entity['name']}()
    assert {entity_name} is not None
    assert isinstance({entity_name}.created_at, datetime)
    assert isinstance({entity_name}.updated_at, datetime)

def test_{entity_name}_attributes():
    \"\"\"Test {entity_name} attributes.\"\"\"
    # TODO: Implement test
    {entity_name} = {entity['name']}()
    # Add assertions for each attribute
""")
            
            logger.info(f"Generated model test: {test_file}")
    
    def _generate_controller_tests(self) -> None:
        """Generate tests for controllers."""
        if "dataModel" not in self.specification or "entities" not in self.specification["dataModel"]:
            return
        
        for entity in self.specification["dataModel"]["entities"]:
            entity_name = entity["name"].lower()
            test_file = os.path.join(self.output_dir, f"tests/test_{entity_name}_controller.py")
            
            with open(test_file, 'w', encoding='utf-8') as file:
                file.write(f"""#!/usr/bin/env python3
\"\"\"
Tests for {entity['name']} controller.
\"\"\"

import pytest
import json
from src.app import app

@pytest.fixture
def client():
    \"\"\"Test client.\"\"\"
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_get_all_{entity_name}s(client):
    \"\"\"Test get all {entity_name}s.\"\"\"
    response = client.get('/{entity_name}s/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "message" in data

def test_get_{entity_name}(client):
    \"\"\"Test get {entity_name}.\"\"\"
    response = client.get('/{entity_name}s/1')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "message" in data

def test_create_{entity_name}(client):
    \"\"\"Test create {entity_name}.\"\"\"
    response = client.post('/{entity_name}s/', json={{}})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "message" in data
    assert "data" in data

def test_update_{entity_name}(client):
    \"\"\"Test update {entity_name}.\"\"\"
    response = client.put('/{entity_name}s/1', json={{}})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "message" in data
    assert "data" in data

def test_delete_{entity_name}(client):
    \"\"\"Test delete {entity_name}.\"\"\"
    response = client.delete('/{entity_name}s/1')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "message" in data
""")
            
            logger.info(f"Generated controller test: {test_file}")
    
    def _generate_integration_tests(self) -> None:
        """Generate integration tests."""
        test_file = os.path.join(self.output_dir, "tests/test_integration.py")
        
        with open(test_file, 'w', encoding='utf-8') as file:
            file.write("""#!/usr/bin/env python3
\"\"\"
Integration tests.
\"\"\"

import pytest
from src.app import app

@pytest.fixture
def client():
    \"\"\"Test client.\"\"\"
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index(client):
    \"\"\"Test index route.\"\"\"
    response = client.get('/')
    assert response.status_code == 200
    assert b"Welcome" in response.data
""")
        
        logger.info(f"Generated integration test: {test_file}")


class BugFixer:
    """Identifies and fixes bugs in the generated code."""
    
    def __init__(self, code_dir: str, test_dir: str):
        """
        Initialize the BugFixer.
        
        Args:
            code_dir: Directory containing the generated code
            test_dir: Directory containing the generated tests
        """
        self.code_dir = code_dir
        self.test_dir = test_dir
    
    def run_tests(self) -> Tuple[bool, str]:
        """
        Run tests to identify bugs.
        
        Returns:
            Tuple of (success, output)
        """
        logger.info("Running tests...")
        
        # In a real implementation, this would run the tests and capture the output
        # For now, we'll simulate a successful test run
        
        return True, "All tests passed"
    
    def identify_bugs(self, test_output: str) -> List[Dict[str, Any]]:
        """
        Identify bugs from test output.
        
        Args:
            test_output: Output from running tests
            
        Returns:
            List of identified bugs
        """
        logger.info("Identifying bugs...")
        
        # In a real implementation, this would parse the test output
        # and identify bugs
        
        # Placeholder for identified bugs
        bugs = []
        
        return bugs
    
    def fix_bugs(self, bugs: List[Dict[str, Any]]) -> None:
        """
        Fix identified bugs.
        
        Args:
            bugs: List of identified bugs
        """
        logger.info("Fixing bugs...")
        
        # In a real implementation, this would fix the identified bugs
        
        for bug in bugs:
            logger.info(f"Fixed bug: {bug}")
    
    def fix(self) -> None:
        """Identify and fix bugs in the generated code."""
        logger.info("Starting bug fixing...")
        
        # Run tests
        success, output = self.run_tests()
        
        if success:
            logger.info("All tests passed, no bugs to fix")
            return
        
        # Identify bugs
        bugs = self.identify_bugs(output)
        
        if not bugs:
            logger.info("No bugs identified")
            return
        
        # Fix bugs
        self.fix_bugs(bugs)
        
        # Run tests again to verify fixes
        success, output = self.run_tests()
        
        if success:
            logger.info("All bugs fixed")
        else:
            logger.warning("Some bugs remain after fixing")
        
        logger.info("Bug fixing completed")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Generate code, tests, and fix bugs based on JSON specifications")
    parser.add_argument("--specification", "-s", type=str, default="output/specification.json",
                        help="Path to the JSON specification file")
    parser.add_argument("--output", "-o", type=str, default="output/generated_code",
                        help="Directory where generated code will be saved")
    parser.add_argument("--prompts-dir", "-p", type=str, default="prompts",
                        help="Directory containing prompt files")
    
    args = parser.parse_args()
    
    # Generate code
    code_generator = CodeGenerator(args.specification, args.output, args.prompts_dir)
    code_generator.generate_code()
    
    # Generate tests
    test_generator = TestGenerator(args.specification, args.output, args.output)
    test_generator.generate_tests()
    
    # Fix bugs
    bug_fixer = BugFixer(args.output, os.path.join(args.output, "tests"))
    bug_fixer.fix()


if __name__ == "__main__":
    main()
