import unittest
import json
import tempfile
import os
import shutil
from unittest.mock import patch, MagicMock
from coding_agent import (
    validate_json_design, 
    validate_json_spec,
    parse_json_and_generate_scaffold_plan,
    create_project_structure
)

class TestCodingAgent(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.sample_design = {
            "system_Architecture": {"components": []},
            "data_Design": {"storage_Type": "sqlite"},
            "interface_Design": {"api_Specifications": []},
            "folder_Structure": {
                "root_Project_Directory_Name": "test_app",
                "structure": [
                    {"path": "main.py", "description": "Main application file"},
                    {"path": "frontend/index.html", "description": "Frontend HTML file"},
                    {"path": "frontend/css/style.css", "description": "CSS stylesheet"},
                    {"path": "frontend/js/app.js", "description": "JavaScript file"}
                ]
            },
            "dependencies": {
                "backend": ["fastapi", "uvicorn"],
                "frontend": []
            }
        }
        
        self.sample_spec = {
            "project_Overview": {
                "project_Name": "Test Application",
                "project_Purpose": "Testing the coding agent"
            },
            "functional_Requirements": [],
            "technology_Stack": {
                "backend": {"language": "Python", "framework": "FastAPI"},
                "frontend": {"language": "HTML/CSS/JS", "framework": "Vanilla"}
            },
            "data_Storage": {"type": "sqlite"}
        }
    
    def test_validate_json_design_success(self):
        """Test successful JSON design validation"""
        try:
            validate_json_design(self.sample_design)
        except ValueError:
            self.fail("validate_json_design raised ValueError unexpectedly")
    
    def test_validate_json_design_missing_field(self):
        """Test JSON design validation with missing field"""
        invalid_design = self.sample_design.copy()
        del invalid_design['system_Architecture']
        
        with self.assertRaises(ValueError) as context:
            validate_json_design(invalid_design)
        
        self.assertIn("system_Architecture", str(context.exception))
    
    def test_validate_json_spec_success(self):
        """Test successful JSON spec validation"""
        try:
            validate_json_spec(self.sample_spec)
        except ValueError:
            self.fail("validate_json_spec raised ValueError unexpectedly")
    
    def test_parse_json_and_generate_scaffold_plan(self):
        """Test scaffold plan generation"""
        plan = parse_json_and_generate_scaffold_plan(self.sample_design, self.sample_spec)
        
        self.assertIn("project_root_directory", plan)
        self.assertIn("directories_to_create", plan)
        self.assertIn("files_to_create", plan)
        self.assertIn("backend_module_path", plan)
        self.assertIn("frontend_dir", plan)
        
        # Check that main.py is detected as backend
        self.assertEqual(plan["backend_module_path"], "main")
        
        # Check that frontend directory is detected
        self.assertEqual(plan["frontend_dir"], "frontend")
    
    def test_create_project_structure(self):
        """Test project structure creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Modify the plan to use temp directory
            plan = parse_json_and_generate_scaffold_plan(self.sample_design, self.sample_spec)
            plan["project_root_directory"] = os.path.join(temp_dir, "test_app")
            
            # Update file paths to use temp directory
            new_files = {}
            for file_path in plan["files_to_create"].keys():
                new_path = file_path.replace(plan["project_root_directory"], os.path.join(temp_dir, "test_app"))
                new_files[new_path] = ""
            plan["files_to_create"] = new_files
            
            # Update directory paths
            new_dirs = []
            for dir_path in plan["directories_to_create"]:
                new_path = dir_path.replace(plan["project_root_directory"], os.path.join(temp_dir, "test_app"))
                new_dirs.append(new_path)
            plan["directories_to_create"] = new_dirs
            
            create_project_structure(plan)
            
            # Verify project root exists
            self.assertTrue(os.path.exists(plan["project_root_directory"]))
            
            # Verify some files were created
            for file_path in plan["files_to_create"].keys():
                self.assertTrue(os.path.exists(file_path), f"File {file_path} was not created")

if __name__ == '__main__':
    unittest.main()
