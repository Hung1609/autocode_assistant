import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, mock_open, MagicMock
from io import StringIO

# Add the current directory to Python path to allow importing detect_path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import the module to test
import detect_path
from detect_path import (
    _get_persistent_value,
    _save_persistent_value,
    _prompt_user,
    define_project_root,
    define_python_path
)


class TestDetectPath(unittest.TestCase):
    """Test suite for detect_path.py module"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        self.original_env = os.environ.copy()
        
    def tearDown(self):
        """Clean up after each test method."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch('detect_path.load_dotenv')
    @patch('detect_path.os.getenv')
    def test_get_persistent_value_existing_key(self, mock_getenv, mock_load_dotenv):
        """Test _get_persistent_value when key exists in environment"""
        mock_getenv.return_value = "test_value"
        
        result = _get_persistent_value("TEST_KEY", "default_value")
        
        mock_load_dotenv.assert_called_once()
        mock_getenv.assert_called_once_with("TEST_KEY", "default_value")
        self.assertEqual(result, "test_value")

    @patch('detect_path.load_dotenv')
    @patch('detect_path.os.getenv')
    def test_get_persistent_value_missing_key(self, mock_getenv, mock_load_dotenv):
        """Test _get_persistent_value when key doesn't exist in environment"""
        mock_getenv.return_value = "default_value"
        
        result = _get_persistent_value("NONEXISTENT_KEY", "default_value")
        
        mock_load_dotenv.assert_called_once()
        mock_getenv.assert_called_once_with("NONEXISTENT_KEY", "default_value")
        self.assertEqual(result, "default_value")

    @patch('detect_path.find_dotenv')
    @patch('detect_path.set_key')
    @patch('builtins.print')
    def test_save_persistent_value_existing_dotenv(self, mock_print, mock_set_key, mock_find_dotenv):
        """Test _save_persistent_value when .env file exists"""
        mock_find_dotenv.return_value = "/path/to/.env"
        
        _save_persistent_value("TEST_KEY", "test_value")
        
        mock_find_dotenv.assert_called_once()
        mock_set_key.assert_called_once_with("/path/to/.env", key_to_set="TEST_KEY", value_to_set="test_value")
        mock_print.assert_called_once_with("✅ Đã cập nhật cấu hình: TEST_KEY trong file /path/to/.env")

    @patch('detect_path.find_dotenv')
    @patch('detect_path.set_key')
    @patch('detect_path.os.path.join')
    @patch('detect_path.os.getcwd')
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    def test_save_persistent_value_no_dotenv(self, mock_print, mock_file, mock_getcwd, 
                                           mock_join, mock_set_key, mock_find_dotenv):
        """Test _save_persistent_value when .env file doesn't exist"""
        mock_find_dotenv.return_value = ""
        mock_getcwd.return_value = "/current/dir"
        mock_join.return_value = "/current/dir/.env"
        
        _save_persistent_value("TEST_KEY", "test_value")
        
        mock_find_dotenv.assert_called_once()
        mock_getcwd.assert_called_once()
        mock_join.assert_called_once_with("/current/dir", '.env')
        mock_file.assert_called_once_with("/current/dir/.env", 'a')
        mock_set_key.assert_called_once_with("/current/dir/.env", key_to_set="TEST_KEY", value_to_set="test_value")

    @patch('builtins.input')
    @patch('builtins.print')
    def test_prompt_user_with_input(self, mock_print, mock_input):
        """Test _prompt_user when user provides input"""
        mock_input.return_value = "user_input"
        
        result = _prompt_user("Test message", "default_value")
        
        mock_input.assert_called_once_with("Test message [Mặc định: default_value]: ")
        self.assertEqual(result, "user_input")

    @patch('builtins.input')
    @patch('builtins.print')
    def test_prompt_user_empty_input(self, mock_print, mock_input):
        """Test _prompt_user when user provides empty input (should use default)"""
        mock_input.return_value = ""
        
        result = _prompt_user("Test message", "default_value")
        
        mock_input.assert_called_once_with("Test message [Mặc định: default_value]: ")
        self.assertEqual(result, "default_value")

    @patch('builtins.input')
    @patch('builtins.print')
    def test_prompt_user_whitespace_input(self, mock_print, mock_input):
        """Test _prompt_user when user provides whitespace-only input (should use default)"""
        mock_input.return_value = "   "
        
        result = _prompt_user("Test message", "default_value")
        
        mock_input.assert_called_once_with("Test message [Mặc định: default_value]: ")
        self.assertEqual(result, "default_value")

    @patch('builtins.input')
    @patch('builtins.print')
    def test_prompt_user_eof_error(self, mock_print, mock_input):
        """Test _prompt_user when EOFError is raised (should use default)"""
        mock_input.side_effect = EOFError()
        
        result = _prompt_user("Test message", "default_value")
        
        mock_input.assert_called_once_with("Test message [Mặc định: default_value]: ")
        mock_print.assert_called_once_with("⚠️ Không nhận được đầu vào từ người dùng, sử dụng giá trị mặc định.")
        self.assertEqual(result, "default_value")

    @patch('detect_path._save_persistent_value')
    @patch('detect_path._prompt_user')
    @patch('detect_path._get_persistent_value')
    @patch('detect_path.os.makedirs')
    @patch('detect_path.os.path.abspath')
    @patch('detect_path.os.path.expanduser')
    @patch('detect_path.os.path.join')
    @patch('detect_path.os.getcwd')
    @patch('builtins.print')
    def test_define_project_root_with_user_input(self, mock_print, mock_getcwd, mock_join,
                                                mock_expanduser, mock_abspath, mock_makedirs,
                                                mock_get_persistent, mock_prompt_user, mock_save_persistent):
        """Test define_project_root when user provides input"""
        mock_getcwd.return_value = "/current/dir"
        mock_join.return_value = "/current/dir/code_generated_result"
        mock_get_persistent.return_value = "/current/dir/code_generated_result"
        mock_prompt_user.return_value = "/user/specified/path"
        mock_expanduser.return_value = "/user/specified/path"
        mock_abspath.return_value = "/user/specified/path"
        
        with patch.dict(os.environ, {}, clear=True):
            result = define_project_root()
        
        mock_get_persistent.assert_called_once_with(
            "PERSISTED_BASE_OUTPUT_DIR",
            "/current/dir/code_generated_result"
        )
        mock_prompt_user.assert_called_once_with("Nhập thư mục gốc để chứa các dự án", "/current/dir/code_generated_result")
        mock_expanduser.assert_called_once_with("/user/specified/path")
        mock_abspath.assert_called_once_with("/user/specified/path")
        mock_makedirs.assert_called_once_with("/user/specified/path", exist_ok=True)
        mock_save_persistent.assert_called_once_with("PERSISTED_BASE_OUTPUT_DIR", "/user/specified/path")
        self.assertEqual(result, "/user/specified/path")
        # Since we're mocking everything, we can't check the actual environment
        # but we can verify the function returned the correct result

    @patch('detect_path._save_persistent_value')
    @patch('detect_path._prompt_user')
    @patch('detect_path._get_persistent_value')
    @patch('detect_path.os.makedirs')
    @patch('detect_path.os.path.abspath')
    @patch('detect_path.os.path.expanduser')
    @patch('detect_path.os.path.join')
    @patch('detect_path.os.getcwd')
    @patch('builtins.print')
    def test_define_project_root_default_path(self, mock_print, mock_getcwd, mock_join,
                                            mock_expanduser, mock_abspath, mock_makedirs,
                                            mock_get_persistent, mock_prompt_user, mock_save_persistent):
        """Test define_project_root when user uses default path"""
        mock_getcwd.return_value = "/current/dir"
        mock_join.return_value = "/current/dir/code_generated_result"
        mock_get_persistent.return_value = "/current/dir/code_generated_result"
        mock_prompt_user.return_value = "/current/dir/code_generated_result"  # User chose default
        mock_expanduser.return_value = "/current/dir/code_generated_result"
        mock_abspath.return_value = "/current/dir/code_generated_result"
        
        with patch.dict(os.environ, {}, clear=True):
            result = define_project_root()
        
        mock_get_persistent.assert_called_once_with(
            "PERSISTED_BASE_OUTPUT_DIR",
            "/current/dir/code_generated_result"
        )
        mock_prompt_user.assert_called_once_with("Nhập thư mục gốc để chứa các dự án", "/current/dir/code_generated_result")
        mock_expanduser.assert_called_once_with("/current/dir/code_generated_result")
        mock_abspath.assert_called_once_with("/current/dir/code_generated_result")
        mock_makedirs.assert_called_once_with("/current/dir/code_generated_result", exist_ok=True)
        mock_save_persistent.assert_called_once_with("PERSISTED_BASE_OUTPUT_DIR", "/current/dir/code_generated_result")
        self.assertEqual(result, "/current/dir/code_generated_result")
        # Since we're mocking everything, we can't check the actual environment

    @patch('detect_path._save_persistent_value')
    @patch('detect_path._prompt_user')
    @patch('detect_path._get_persistent_value')
    @patch('detect_path.os.makedirs')
    @patch('detect_path.os.path.abspath')
    @patch('detect_path.os.path.expanduser')
    @patch('detect_path.os.path.join')
    @patch('detect_path.os.getcwd')
    @patch('builtins.print')
    def test_define_project_root_with_home_directory(self, mock_print, mock_getcwd, mock_join,
                                                   mock_expanduser, mock_abspath, mock_makedirs,
                                                   mock_get_persistent, mock_prompt_user, mock_save_persistent):
        """Test define_project_root with home directory expansion"""
        mock_getcwd.return_value = "/current/dir"
        mock_join.return_value = "/current/dir/code_generated_result"
        mock_get_persistent.return_value = "/current/dir/code_generated_result"
        mock_prompt_user.return_value = "~/my_projects"
        mock_expanduser.return_value = "/home/user/my_projects"
        mock_abspath.return_value = "/home/user/my_projects"
        
        with patch.dict(os.environ, {}, clear=True):
            result = define_project_root()
        
        mock_prompt_user.assert_called_once_with("Nhập thư mục gốc để chứa các dự án", "/current/dir/code_generated_result")
        mock_expanduser.assert_called_once_with("~/my_projects")
        mock_abspath.assert_called_once_with("/home/user/my_projects")
        mock_makedirs.assert_called_once_with("/home/user/my_projects", exist_ok=True)
        self.assertEqual(result, "/home/user/my_projects")

    @patch('detect_path._save_persistent_value')
    @patch('detect_path._prompt_user')
    @patch('detect_path._get_persistent_value')
    @patch('detect_path.os.path.isfile')
    @patch('detect_path.os.path.abspath')
    @patch('detect_path.os.path.expanduser')
    @patch('detect_path.sys.executable', '/usr/bin/python3')
    @patch('builtins.print')
    def test_define_python_path_with_user_input(self, mock_print, mock_expanduser, mock_abspath,
                                               mock_isfile, mock_get_persistent, mock_prompt_user, mock_save_persistent):
        """Test define_python_path when user provides input"""
        mock_get_persistent.return_value = "/usr/bin/python3"
        mock_prompt_user.return_value = "/user/python/path"
        mock_expanduser.return_value = "/user/python/path"
        mock_abspath.return_value = "/user/python/path"
        mock_isfile.return_value = True  # File exists
        
        with patch.dict(os.environ, {}, clear=True):
            result = define_python_path()
        
        mock_get_persistent.assert_called_once_with("PERSISTED_PYTHON_PATH", "/usr/bin/python3")
        mock_prompt_user.assert_called_once_with("Nhập đường dẫn đến trình thực thi Python", "/usr/bin/python3")
        mock_expanduser.assert_called_once_with("/user/python/path")
        mock_abspath.assert_called_once_with("/user/python/path")
        mock_isfile.assert_called_once_with("/user/python/path")
        mock_save_persistent.assert_called_once_with("PERSISTED_PYTHON_PATH", "/user/python/path")
        self.assertEqual(result, "/user/python/path")
        # Since we're mocking everything, we can't check the actual environment

    @patch('detect_path._save_persistent_value')
    @patch('detect_path._prompt_user')
    @patch('detect_path._get_persistent_value')
    @patch('detect_path.os.path.isfile')
    @patch('detect_path.os.path.abspath')
    @patch('detect_path.os.path.expanduser')
    @patch('detect_path.sys.executable', '/usr/bin/python3')
    @patch('builtins.print')
    def test_define_python_path_default_path(self, mock_print, mock_expanduser, mock_abspath,
                                           mock_isfile, mock_get_persistent, mock_prompt_user, mock_save_persistent):
        """Test define_python_path when user uses default path"""
        mock_get_persistent.return_value = "/usr/bin/python3"
        mock_prompt_user.return_value = "/usr/bin/python3"  # User chose default
        mock_expanduser.return_value = "/usr/bin/python3"
        mock_abspath.return_value = "/usr/bin/python3"
        mock_isfile.return_value = True  # File exists
        
        with patch.dict(os.environ, {}, clear=True):
            result = define_python_path()
        
        mock_get_persistent.assert_called_once_with("PERSISTED_PYTHON_PATH", "/usr/bin/python3")
        mock_prompt_user.assert_called_once_with("Nhập đường dẫn đến trình thực thi Python", "/usr/bin/python3")
        mock_expanduser.assert_called_once_with("/usr/bin/python3")
        mock_abspath.assert_called_once_with("/usr/bin/python3")
        mock_isfile.assert_called_once_with("/usr/bin/python3")
        mock_save_persistent.assert_called_once_with("PERSISTED_PYTHON_PATH", "/usr/bin/python3")
        self.assertEqual(result, "/usr/bin/python3")
        # Since we're mocking everything, we can't check the actual environment

    @patch('detect_path._save_persistent_value')
    @patch('detect_path._prompt_user')
    @patch('detect_path._get_persistent_value')
    @patch('detect_path.os.path.isfile')
    @patch('detect_path.os.path.abspath')
    @patch('detect_path.os.path.expanduser')
    @patch('detect_path.sys.executable', '/usr/bin/python3')
    @patch('builtins.print')
    def test_define_python_path_invalid_file(self, mock_print, mock_expanduser, mock_abspath,
                                           mock_isfile, mock_get_persistent, mock_prompt_user, mock_save_persistent):
        """Test define_python_path when file doesn't exist (should show warning)"""
        mock_get_persistent.return_value = "/usr/bin/python3"
        mock_prompt_user.return_value = "/invalid/python/path"
        mock_expanduser.return_value = "/invalid/python/path"
        mock_abspath.return_value = "/invalid/python/path"
        mock_isfile.return_value = False  # File doesn't exist
        
        with patch.dict(os.environ, {}, clear=True):
            result = define_python_path()
        
        mock_get_persistent.assert_called_once_with("PERSISTED_PYTHON_PATH", "/usr/bin/python3")
        mock_prompt_user.assert_called_once_with("Nhập đường dẫn đến trình thực thi Python", "/usr/bin/python3")
        mock_expanduser.assert_called_once_with("/invalid/python/path")
        mock_abspath.assert_called_once_with("/invalid/python/path")
        mock_isfile.assert_called_once_with("/invalid/python/path")
        # Check that warning was printed
        warning_calls = [call for call in mock_print.call_args_list if "⚠️ Cảnh báo" in str(call)]
        self.assertTrue(len(warning_calls) > 0)
        mock_save_persistent.assert_called_once_with("PERSISTED_PYTHON_PATH", "/invalid/python/path")
        self.assertEqual(result, "/invalid/python/path")
        # Since we're mocking everything, we can't check the actual environment

    @patch('detect_path._save_persistent_value')
    @patch('detect_path._prompt_user')
    @patch('detect_path._get_persistent_value')
    @patch('detect_path.os.path.isfile')
    @patch('detect_path.os.path.abspath')
    @patch('detect_path.os.path.expanduser')
    @patch('detect_path.sys.executable', '/usr/bin/python3')
    @patch('builtins.print')
    def test_define_python_path_with_home_directory(self, mock_print, mock_expanduser, mock_abspath,
                                                  mock_isfile, mock_get_persistent, mock_prompt_user, mock_save_persistent):
        """Test define_python_path with home directory expansion"""
        mock_get_persistent.return_value = "/usr/bin/python3"
        mock_prompt_user.return_value = "~/bin/python"
        mock_expanduser.return_value = "/home/user/bin/python"
        mock_abspath.return_value = "/home/user/bin/python"
        mock_isfile.return_value = True  # File exists
        
        with patch.dict(os.environ, {}, clear=True):
            result = define_python_path()
        
        mock_prompt_user.assert_called_once_with("Nhập đường dẫn đến trình thực thi Python", "/usr/bin/python3")
        mock_expanduser.assert_called_once_with("~/bin/python")
        mock_abspath.assert_called_once_with("/home/user/bin/python")
        mock_isfile.assert_called_once_with("/home/user/bin/python")
        self.assertEqual(result, "/home/user/bin/python")


class TestDetectPathIntegration(unittest.TestCase):
    """Integration tests for detect_path.py module"""

    def setUp(self):
        """Set up test fixtures for integration tests."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        self.original_env = os.environ.copy()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up after integration tests."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch('detect_path._prompt_user')
    def test_full_workflow_project_root(self, mock_prompt_user):
        """Test the full workflow of setting up project root"""
        mock_prompt_user.return_value = 'my_projects'
        
        result = define_project_root()
        
        # Check that directory was created
        expected_path = os.path.abspath(os.path.join(self.test_dir, 'my_projects'))
        self.assertTrue(os.path.exists(expected_path))
        self.assertEqual(result, expected_path)
        self.assertEqual(os.environ.get('BASE_OUTPUT_DIR'), expected_path)

    @patch('detect_path._prompt_user')
    def test_full_workflow_python_path(self, mock_prompt_user):
        """Test the full workflow of setting up Python path"""
        test_python_path = '/test/python/path'
        mock_prompt_user.return_value = test_python_path
        
        result = define_python_path()
        
        expected_path = os.path.abspath(test_python_path)
        self.assertEqual(result, expected_path)
        self.assertEqual(os.environ.get('PYTHON_PATH'), expected_path)


if __name__ == '__main__':
    # Create a test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestDetectPath)
    integration_suite = unittest.TestLoader().loadTestsFromTestCase(TestDetectPathIntegration)
    
    # Combine test suites
    combined_suite = unittest.TestSuite([test_suite, integration_suite])
    
    # Run the tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(combined_suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
