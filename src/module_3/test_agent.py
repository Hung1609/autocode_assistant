import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import os
import json
import shutil
import logging
logging.disable(logging.CRITICAL)

# Import the module to be tested
import agent

# Disable logging for cleaner test output (optional)
# logging.disable(logging.CRITICAL)

# Define a dummy test output directory
TEST_OUTPUT_DIR = 'test_code_generated_result'

# --- Helper Functions/Data for Tests ---

def get_valid_design_json():
    """Returns a minimal valid JSON design structure."""
    return {
        "metadata": {"source_specification_timestamp": "2023-01-01T12:00:00Z"},
        "system_Architecture": {"description": "Test Arch"},
        "data_Design": {"storage_Type": "PostgreSQL", "models": []},
        "interface_Design": {"api_Specifications": []},
        "folder_Structure": {
            "structure": [
                {"path": "/backend", "description": "Backend directory"},
                {"path": "/backend/main.py", "description": "Main backend file"},
                {"path": "/frontend", "description": "Frontend directory"},
                {"path": "/frontend/src/App.js", "description": "Main frontend component"}
            ]
        },
        "dependencies": {
            "backend": ["flask", "sqlalchemy"],
            "frontend": ["react", "axios"]
        },
         "workflow_Interaction": [] # Added for completeness based on prompt description
    }

def get_valid_spec_json():
    """Returns a minimal valid JSON specification structure."""
    return {
        "metadata": {"timestamp": "2023-01-01T12:00:00Z"},
        "project_Overview": {"project_Name": "TestApp"},
        "functional_Requirements": [{"id": "FR001", "description": "Test requirement"}],
        "non_Functional_Requirements": [], # Added for completeness based on prompt description
        "technology_Stack": {
             "backend": {"framework": "Flask"},
             "frontend": {"framework": "React"}
        }
    }

# --- Test Class ---

class TestAgent(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure the original OUTPUT_DIR doesn't interfere if it exists
        if os.path.exists(agent.OUTPUT_DIR):
            print(f"Warning: Original output directory '{agent.OUTPUT_DIR}' exists. Consider removing it.")

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for test outputs
        self.test_output_dir = TEST_OUTPUT_DIR
        os.makedirs(self.test_output_dir, exist_ok=True)
        # IMPORTANT: Patch the OUTPUT_DIR constant within the agent module for the duration of the test
        self.output_dir_patcher = patch('agent.OUTPUT_DIR', self.test_output_dir)
        self.output_dir_patcher.start()

    def tearDown(self):
        """Clean up test environment after each test."""
        # Stop the patch
        self.output_dir_patcher.stop()
        # Remove the temporary directory
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    # === Test validate_json_design ===

    def test_validate_json_design_valid(self):
        """Test validate_json_design with valid data."""
        valid_data = get_valid_design_json()
        try:
            agent.validate_json_design(valid_data)
        except ValueError:
            self.fail("validate_json_design raised ValueError unexpectedly!")

    def test_validate_json_design_missing_required_field(self):
        """Test validate_json_design missing a top-level field."""
        invalid_data = get_valid_design_json()
        del invalid_data['data_Design']
        with self.assertRaisesRegex(ValueError, "JSON design file must contain 'data_Design'"):
            agent.validate_json_design(invalid_data)

    def test_validate_json_design_invalid_folder_structure_type(self):
        """Test validate_json_design with non-list folder_Structure.structure."""
        invalid_data = get_valid_design_json()
        invalid_data['folder_Structure']['structure'] = "not a list"
        with self.assertRaisesRegex(ValueError, "folder_Structure.structure must be a list"):
            agent.validate_json_design(invalid_data)

    def test_validate_json_design_invalid_folder_structure_item(self):
        """Test validate_json_design with folder_Structure item missing 'path'."""
        invalid_data = get_valid_design_json()
        invalid_data['folder_Structure']['structure'][0] = {"description": "missing path"}
        with self.assertRaisesRegex(ValueError, "Each folder_Structure item must have a 'path'"):
            agent.validate_json_design(invalid_data)

    def test_validate_json_design_missing_dependencies_key(self):
        """Test validate_json_design missing backend/frontend in dependencies."""
        invalid_data_backend = get_valid_design_json()
        del invalid_data_backend['dependencies']['backend']
        with self.assertRaisesRegex(ValueError, "dependencies must contain 'backend' and 'frontend'"):
            agent.validate_json_design(invalid_data_backend)

        invalid_data_frontend = get_valid_design_json()
        del invalid_data_frontend['dependencies']['frontend']
        with self.assertRaisesRegex(ValueError, "dependencies must contain 'backend' and 'frontend'"):
            agent.validate_json_design(invalid_data_frontend)

    # === Test validate_json_spec ===

    def test_validate_json_spec_valid(self):
        """Test validate_json_spec with valid data."""
        valid_data = get_valid_spec_json()
        try:
            agent.validate_json_spec(valid_data)
        except ValueError:
            self.fail("validate_json_spec raised ValueError unexpectedly!")

    def test_validate_json_spec_missing_required_field(self):
        """Test validate_json_spec missing a required field."""
        invalid_data = get_valid_spec_json()
        del invalid_data['functional_Requirements']
        with self.assertRaisesRegex(ValueError, "JSON specification must contain 'functional_Requirements'"):
            agent.validate_json_spec(invalid_data)

    # === Test parse_json_and_generate_scaffold_plan ===

    def test_parse_json_and_generate_scaffold_plan_success(self):
        """Test parse_json_and_generate_scaffold_plan successful execution."""
        json_design = get_valid_design_json()

        # Expected output based DIRECTLY on the function's logic:
        expected_dirs_explicit = [
            os.path.join(self.test_output_dir, 'backend'),
            os.path.join(self.test_output_dir, 'frontend')
        ]
        expected_files_from_structure = {
            os.path.join(self.test_output_dir, 'backend/main.py'): "",
            os.path.join(self.test_output_dir, 'frontend/src/App.js'): ""
        }
        expected_dependency_files = {
            os.path.join(self.test_output_dir, 'backend/requirements.txt'): "",
            os.path.join(self.test_output_dir, 'frontend/package.json'): ""
        }
        expected_files_all = {**expected_files_from_structure, **expected_dependency_files} # Combine file dicts

        # The 'shell' list in the plan is for logging: mkdir for explicit dirs, touch for ALL files
        expected_shell = sorted(
            [f"mkdir {d}" for d in expected_dirs_explicit] +
            [f"touch {f}" for f in expected_files_all.keys()]
        )


        plan = agent.parse_json_and_generate_scaffold_plan(json_design)

        self.assertIsInstance(plan, dict)
        self.assertIn("shell", plan)
        self.assertIn("files", plan)
        self.assertIsInstance(plan["shell"], list)
        self.assertIsInstance(plan["files"], dict)

        # Compare files dict (most important)
        self.assertDictEqual(plan["files"], expected_files_all)
        # Compare shell list (less critical, for logging)
        self.assertListEqual(sorted(plan["shell"]), expected_shell) # Compare sorted lists

    def test_parse_json_and_generate_scaffold_plan_invalid_json(self):
        """Test parse_json_and_generate_scaffold_plan with invalid JSON input."""
        invalid_json = get_valid_design_json()
        del invalid_json['folder_Structure']
        with self.assertRaises(ValueError):
            agent.parse_json_and_generate_scaffold_plan(invalid_json)

    # === Test create_project_structure ===

    @patch('os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_create_project_structure_success(self, mock_file_open, mock_makedirs):
        """Test create_project_structure successfully creates dirs and files."""
        plan = {
            "shell": [
                f"mkdir {self.test_output_dir}/dir1",
                f"mkdir {self.test_output_dir}/dir2",
                f"touch {self.test_output_dir}/dir1/file1.txt",
                f"touch {self.test_output_dir}/file2.py"
            ],
            "files": {
                os.path.join(self.test_output_dir, 'dir1/file1.txt'): "",
                os.path.join(self.test_output_dir, 'file2.py'): ""
            }
        }

        agent.create_project_structure(plan)

        # Check if OUTPUT_DIR itself was created (or attempted)
        mock_makedirs.assert_any_call(self.test_output_dir, exist_ok=True)

        # Check directory creation calls based on file paths
        expected_dirs_to_create = {
            os.path.dirname(os.path.join(self.test_output_dir, 'dir1/file1.txt')), # -> test_output_dir/dir1
             # os.path.dirname(os.path.join(self.test_output_dir, 'file2.py')) # -> test_output_dir (already handled)
        }
        # Filter out the base output dir as it's handled separately
        expected_dirs_to_create = {d for d in expected_dirs_to_create if d != self.test_output_dir}

        calls_makedirs = [call(d, exist_ok=True) for d in sorted(list(expected_dirs_to_create))]
        mock_makedirs.assert_has_calls(calls_makedirs, any_order=True)


        # Check file creation calls
        calls_open = [
            call(os.path.join(self.test_output_dir, 'dir1/file1.txt'), 'w', encoding='utf-8'),
            call(os.path.join(self.test_output_dir, 'file2.py'), 'w', encoding='utf-8')
        ]
        mock_file_open.assert_has_calls(calls_open, any_order=True)
        # Check that files were 'written' (mocked write)
        self.assertEqual(mock_file_open().write.call_count, 0) # Should be empty files

    @patch('os.makedirs', side_effect=OSError("Permission denied"))
    def test_create_project_structure_makedirs_fails(self, mock_makedirs):
        """Test create_project_structure when directory creation fails."""
        plan = {"files": {os.path.join(self.test_output_dir, 'dir1/file1.txt'): ""}}
        # We expect the first call to makedirs (for OUTPUT_DIR) to fail
        with self.assertRaisesRegex(OSError, "Permission denied"):
             # Need to trigger the directory creation part
             # Patching the initial makedirs call
             with patch('agent.os.makedirs', side_effect=OSError("Permission denied")) as mock_make_output:
                 agent.create_project_structure(plan)
                 # Check the initial call failed
                 mock_make_output.assert_called_once_with(self.test_output_dir, exist_ok=True)


    @patch('os.makedirs') # Mock makedirs so it doesn't actually create dirs
    @patch('builtins.open', side_effect=OSError("Cannot open file"))
    def test_create_project_structure_open_fails(self, mock_file_open, mock_makedirs):
        """Test create_project_structure when file creation fails."""
        file_path = os.path.join(self.test_output_dir, 'file1.txt')
        plan = {"files": {file_path: ""}}
        with self.assertRaisesRegex(OSError, "Cannot open file"):
            agent.create_project_structure(plan)
        # Ensure makedirs was called for the directory containing the file
        mock_makedirs.assert_any_call(os.path.dirname(file_path), exist_ok=True)
        # Ensure open was called for the file
        mock_file_open.assert_called_once_with(file_path, 'w', encoding='utf-8')


    # === Test generate_code_for_each_file ===

@patch('agent.GenerativeModel')
@patch('agent.configure') # Mock configure to avoid real API key check
@patch('os.getenv', return_value='fake-api-key') # Mock getenv
# Add mock_configure here
def test_generate_code_for_each_file_api_call(self, mock_getenv, mock_configure, MockGenerativeModel):
    """Test generate_code_for_each_file calls the API for a regular file."""
    mock_model_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Generated Python Code"
    mock_model_instance.generate_content.return_value = mock_response
    MockGenerativeModel.return_value = mock_model_instance

    json_design = get_valid_design_json()
    json_spec = get_valid_spec_json()
    file_path = os.path.join(self.test_output_dir, 'backend/main.py')

    generated_code = agent.generate_code_for_each_file(json_design, json_spec, file_path)

    # Assert configure was called at module level (handled elsewhere or implicitly tested)
    # We don't assert mock_configure call here as generate_code_... doesn't call it directly.

    # Assert model was initialized (trying default first)
    MockGenerativeModel.assert_any_call(agent.DEFAULT_MODEL)
    # Check if generate_content was called
    self.assertTrue(mock_model_instance.generate_content.called)
    # Check the generated code is returned
    self.assertEqual(generated_code, "Generated Python Code")

    # Optionally, check the prompt structure
    call_args, _ = mock_model_instance.generate_content.call_args
    prompt = call_args[0]
    self.assertIn(f"File path: `{file_path}`", prompt)
    self.assertIn(json.dumps(json_design, indent=2), prompt)
    self.assertIn(json.dumps(json_spec, indent=2), prompt)
    self.assertIn("TestApp", prompt) # Project Name
    self.assertIn("Flask", prompt) # Backend Framework
    self.assertIn("React", prompt) # Frontend Framework

    def test_generate_code_for_requirements_txt(self):
        """Test generate_code_for_each_file handles requirements.txt correctly."""
        json_design = get_valid_design_json()
        json_spec = get_valid_spec_json()
        file_path = os.path.join(self.test_output_dir, 'backend/requirements.txt')
        expected_content = "flask\nsqlalchemy"

        # Mock GenerativeModel to ensure API is NOT called
        with patch('agent.GenerativeModel') as MockGenerativeModel:
            generated_code = agent.generate_code_for_each_file(json_design, json_spec, file_path)
            self.assertEqual(generated_code, expected_content)
            MockGenerativeModel.assert_not_called() # Crucial check

    def test_generate_code_for_package_json(self):
        """Test generate_code_for_each_file handles package.json correctly."""
        json_design = get_valid_design_json()
        json_spec = get_valid_spec_json()
        file_path = os.path.join(self.test_output_dir, 'frontend/package.json')
        expected_json = {
            "name": "testapp-frontend",
            "version": "1.0.0",
            "dependencies": {
                "react": "latest",
                "axios": "latest"
            },
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build"
            }
        }
        expected_content = json.dumps(expected_json, indent=2)

        # Mock GenerativeModel to ensure API is NOT called
        with patch('agent.GenerativeModel') as MockGenerativeModel:
            generated_code = agent.generate_code_for_each_file(json_design, json_spec, file_path)
            self.assertEqual(generated_code, expected_content)
            MockGenerativeModel.assert_not_called() # Crucial check

    @patch('agent.GenerativeModel')
    @patch('agent.configure')
    @patch('os.getenv', return_value='fake-api-key')
    def test_generate_code_api_fails(self, mock_getenv, mock_configure, MockGenerativeModel):
        """Test generate_code_for_each_file when API call raises an error."""
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.side_effect = Exception("API Error")
        MockGenerativeModel.return_value = mock_model_instance

        json_design = get_valid_design_json()
        json_spec = get_valid_spec_json()
        file_path = os.path.join(self.test_output_dir, 'backend/main.py')

        with self.assertRaisesRegex(Exception, "API Error"):
            agent.generate_code_for_each_file(json_design, json_spec, file_path)

    @patch('agent.GenerativeModel', side_effect=Exception("Model init failed"))
    @patch('agent.configure')
    @patch('os.getenv', return_value='fake-api-key')
    def test_generate_code_no_models_available(self, mock_getenv, mock_configure, MockGenerativeModel):
        """Test generate_code_for_each_file when no models can be initialized."""
        json_design = get_valid_design_json()
        json_spec = get_valid_spec_json()
        file_path = os.path.join(self.test_output_dir, 'backend/main.py')

        with self.assertRaisesRegex(ValueError, "No supported Gemini models available."):
            agent.generate_code_for_each_file(json_design, json_spec, file_path)

    def test_generate_code_invalid_input_types(self):
        """Test generate_code_for_each_file with invalid input types."""
        with self.assertRaises(ValueError):
            agent.generate_code_for_each_file("not a dict", {}, "path")
        with self.assertRaises(ValueError):
            agent.generate_code_for_each_file({}, "not a dict", "path")
        with self.assertRaises(ValueError):
            agent.generate_code_for_each_file({}, {}, 123) # Not a string path

    # === Test write_code_to_file ===

    @patch('os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_write_code_to_file_success(self, mock_file_open, mock_makedirs):
        """Test write_code_to_file successfully writes content."""
        file_path = os.path.join(self.test_output_dir, 'subdir/test.py')
        code_content = "print('Hello, world!')"
        dir_path = os.path.dirname(file_path)

        agent.write_code_to_file(file_path, code_content)

        # Check directory creation was attempted
        mock_makedirs.assert_called_once_with(dir_path, exist_ok=True)
        # Check file was opened correctly
        mock_file_open.assert_called_once_with(file_path, 'w', encoding='utf-8')
        # Check content was written
        mock_file_open().write.assert_called_once_with(code_content)

    @patch('os.makedirs', side_effect=OSError("Cannot create dir"))
    def test_write_code_to_file_makedirs_fails(self, mock_makedirs):
        """Test write_code_to_file when directory creation fails."""
        file_path = os.path.join(self.test_output_dir, 'subdir/test.py')
        code_content = "print('fail')"
        dir_path = os.path.dirname(file_path)
        with self.assertRaisesRegex(OSError, "Cannot create dir"):
            agent.write_code_to_file(file_path, code_content)
        mock_makedirs.assert_called_once_with(dir_path, exist_ok=True)

    @patch('os.makedirs')
    @patch('builtins.open', side_effect=OSError("Cannot write"))
    def test_write_code_to_file_open_fails(self, mock_file_open, mock_makedirs):
        """Test write_code_to_file when file opening/writing fails."""
        file_path = os.path.join(self.test_output_dir, 'subdir/test.py')
        code_content = "print('fail')"
        dir_path = os.path.dirname(file_path)
        with self.assertRaisesRegex(OSError, "Cannot write"):
            agent.write_code_to_file(file_path, code_content)
        mock_makedirs.assert_called_once_with(dir_path, exist_ok=True)
        mock_file_open.assert_called_once_with(file_path, 'w', encoding='utf-8')

    # === Test run_codegen_pipeline ===

    @patch('agent.write_code_to_file')
    @patch('agent.generate_code_for_each_file')
    @patch('agent.create_project_structure')
    @patch('agent.parse_json_and_generate_scaffold_plan')
    def test_run_codegen_pipeline_success(self, mock_parse, mock_create, mock_generate, mock_write):
        """Test run_codegen_pipeline orchestrates calls correctly on success."""
        json_design = get_valid_design_json()
        json_spec = get_valid_spec_json()
        design_file_path = "dummy_design.json"

        # Setup mock return values
        mock_plan = {
            "shell": ["mock command"],
            "files": {
                os.path.join(self.test_output_dir,"file1.py"): "",
                os.path.join(self.test_output_dir,"file2.js"): ""
            }
        }
        mock_parse.return_value = mock_plan
        mock_generate.side_effect = ["code for file1", "code for file2"] # Return different code for each call

        agent.run_codegen_pipeline(json_design, json_spec, design_file_path)

        # Assert functions were called with correct args
        mock_parse.assert_called_once_with(json_design)
        mock_create.assert_called_once_with(mock_plan)

        # Assert generate and write were called for each file in the plan
        expected_generate_calls = [
            call(json_design, json_spec, os.path.join(self.test_output_dir, "file1.py")),
            call(json_design, json_spec, os.path.join(self.test_output_dir, "file2.js"))
        ]
        mock_generate.assert_has_calls(expected_generate_calls, any_order=False) # Order matters here

        expected_write_calls = [
            call(os.path.join(self.test_output_dir, "file1.py"), "code for file1"),
            call(os.path.join(self.test_output_dir, "file2.js"), "code for file2")
        ]
        mock_write.assert_has_calls(expected_write_calls, any_order=False) # Order matters here

    @patch('agent.parse_json_and_generate_scaffold_plan', side_effect=ValueError("Parsing failed"))
    def test_run_codegen_pipeline_parse_fails(self, mock_parse):
        """Test run_codegen_pipeline when parsing fails."""
        with self.assertRaisesRegex(ValueError, "Parsing failed"):
            agent.run_codegen_pipeline({}, {}, "dummy.json")

    @patch('agent.parse_json_and_generate_scaffold_plan')
    @patch('agent.create_project_structure', side_effect=OSError("Create failed"))
    def test_run_codegen_pipeline_create_fails(self, mock_create, mock_parse):
        """Test run_codegen_pipeline when structure creation fails."""
        mock_parse.return_value = {"files": {}} # Need a valid plan structure
        with self.assertRaisesRegex(OSError, "Create failed"):
            agent.run_codegen_pipeline({}, {}, "dummy.json")

    @patch('agent.write_code_to_file') # Mock write to prevent side effects
    @patch('agent.generate_code_for_each_file', side_effect=Exception("Generate failed"))
    @patch('agent.create_project_structure')
    @patch('agent.parse_json_and_generate_scaffold_plan')
    def test_run_codegen_pipeline_generate_fails(self, mock_parse, mock_create, mock_generate, mock_write):
        """Test run_codegen_pipeline when code generation fails."""
        mock_plan = {"files": {os.path.join(self.test_output_dir,"file1.py"): ""}}
        mock_parse.return_value = mock_plan
        with self.assertRaisesRegex(Exception, "Generate failed"):
            agent.run_codegen_pipeline({}, {}, "dummy.json")
        mock_write.assert_not_called() # Ensure write wasn't called if generate failed

    @patch('agent.write_code_to_file', side_effect=OSError("Write failed"))
    @patch('agent.generate_code_for_each_file', return_value="mock code")
    @patch('agent.create_project_structure')
    @patch('agent.parse_json_and_generate_scaffold_plan')
    def test_run_codegen_pipeline_write_fails(self, mock_parse, mock_create, mock_generate, mock_write):
        """Test run_codegen_pipeline when writing code to file fails."""
        mock_plan = {"files": {os.path.join(self.test_output_dir, "file1.py"): ""}}
        mock_parse.return_value = mock_plan
        with self.assertRaisesRegex(OSError, "Write failed"):
            agent.run_codegen_pipeline({}, {}, "dummy.json")

    # === Test __main__ block (Integration Style - Optional) ===

    @patch('argparse.ArgumentParser.parse_args')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    @patch('agent.run_codegen_pipeline')
    @patch('agent.validate_json_design') # Mock validation called by run_codegen
    @patch('agent.validate_json_spec') # Mock validation called by run_codegen
    def test_main_execution_success(self, mock_val_spec, mock_val_design, mock_run_pipeline, mock_json_load, mock_file_open, mock_parse_args):
        """Test the main execution flow."""
        # Mock command line arguments
        mock_args = MagicMock()
        mock_args.design_file = 'design.json'
        mock_args.spec_file = 'spec.json'
        mock_parse_args.return_value = mock_args

        # Mock JSON data loaded from files
        design_data = get_valid_design_json()
        spec_data = get_valid_spec_json()
        # Make json.load return spec then design data on consecutive calls
        mock_json_load.side_effect = [design_data, spec_data]

        # Mock file handles to be returned by open
        mock_design_handle = mock_open(read_data=json.dumps(design_data)).return_value
        mock_spec_handle = mock_open(read_data=json.dumps(spec_data)).return_value
        # Configure mock_open to return the correct handle based on filename
        def open_side_effect(filename, *args, **kwargs):
            if filename == 'design.json':
                return mock_design_handle
            elif filename == 'spec.json':
                return mock_spec_handle
            else:
                # Raise an error for unexpected file opens
                raise FileNotFoundError(f"Unexpected file open: {filename}")
        mock_file_open.side_effect = open_side_effect

        # Run the main block entry point by importing it (if structure allows)
        # or by calling a wrapper function if you refactor main
        # For this structure, we simulate the execution:
        try:
             # Simulate the if __name__ == "__main__": block's core logic
             args = agent.parser.parse_args() # Uses the mocked parse_args
             with open(args.design_file) as f_design:
                 json_design = json.load(f_design) # Uses mocked open and json.load
             with open(args.spec_file) as f_spec:
                 json_spec = json.load(f_spec) # Uses mocked open and json.load

             # Timestamp check simulation (assuming they match in this test)
             self.assertEqual(
                 json_design.get('metadata', {}).get('source_specification_timestamp'),
                 json_spec.get('metadata', {}).get('timestamp')
             )

             agent.run_codegen_pipeline(json_design, json_spec, args.design_file) # Uses mocked run_pipeline

        except Exception as e:
             self.fail(f"Main block simulation raised an exception unexpectedly: {e}")


        # Assertions
        mock_parse_args.assert_called_once()
        expected_open_calls = [call('design.json'), call('spec.json')]
        mock_file_open.assert_has_calls(expected_open_calls, any_order=True)
        expected_json_load_calls = [call(mock_design_handle), call(mock_spec_handle)]
        mock_json_load.assert_has_calls(expected_json_load_calls)
        mock_run_pipeline.assert_called_once_with(design_data, spec_data, 'design.json')

    @patch('argparse.ArgumentParser.parse_args')
    @patch('builtins.open', side_effect=FileNotFoundError("No such file"))
    def test_main_execution_file_not_found(self, mock_file_open, mock_parse_args):
         """Test the main execution flow when a file is not found."""
         mock_args = MagicMock()
         mock_args.design_file = 'nonexistent_design.json'
         mock_args.spec_file = 'spec.json'
         mock_parse_args.return_value = mock_args

         # Simulate the main block entry point
         with self.assertRaises(FileNotFoundError):
             # Simulate the if __name__ == "__main__": block's core logic
             args = agent.parser.parse_args()
             with open(args.design_file) as f: # This call will raise FileNotFoundError
                 json_design = json.load(f)
             # ... rest of the block won't execute


# --- Run Tests ---
if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)