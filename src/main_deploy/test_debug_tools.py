#!/usr/bin/env python3
"""
Test script to verify the debug agent tools functionality
"""

import os
import sys
import tempfile
import json

# Add the src path to import our debug agent
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'main_deploy'))

from debug_agent import DebuggingTools

def test_debug_tools():
    """Test the debug agent tools"""
    
    # Create a temporary test setup
    test_log_content = """============================= FAILURES =============================
________________________ test_read_tasks_success ________________________

    def test_read_tasks_success():
        # Test successful retrieval of tasks
        db = TestingSession()
        
        # Create test tasks
        task1 = crud.create_task(db, schemas.TaskCreate(title="Task 1", description="First task"))
        task2 = crud.create_task(db, schemas.TaskCreate(title="Task 2", description="Second task"))
        
        response = client.get("/tasks")
        assert response.status_code == 200
        
        tasks = response.json()
>       assert len(tasks) == 2
E       assert 0 == 2
E        +  where 0 = len([])

tests/test_routers.py:45: AssertionError
========================== short test summary info ===========================
FAILED tests/test_routers.py::test_read_tasks_success - assert 0 == 2
=========================== 1 failed, 2 passed in 0.45s ===========================
"""
    
    # Create temporary directory and test files
    with tempfile.TemporaryDirectory() as temp_dir:
        test_log_path = os.path.join(temp_dir, "test_results.log")
        
        # Create test files
        with open(test_log_path, 'w') as f:
            f.write(test_log_content)
        
        # Create a mock source file
        backend_dir = os.path.join(temp_dir, "backend", "routers")
        os.makedirs(backend_dir, exist_ok=True)
        
        source_file_path = os.path.join(backend_dir, "tasks.py")
        with open(source_file_path, 'w') as f:
            f.write("""
# Mock source file
def read_tasks():
    return []  # This is the bug - should return actual tasks
""")
        
        # Create debug tools instance
        tools = DebuggingTools(project_root=temp_dir)
        
        print("Testing debug tools functionality...")
        
        # Test 1: Parse test results
        print("1. Testing test log parsing...")
        failure = tools._parse_test_log_file(test_log_path)
        if failure:
            print(f"   ✅ Successfully parsed failure: {failure['test_name']}")
            print(f"   ✅ Error: {failure['error_summary_line']}")
            print(f"   ✅ Function: {failure['source_function_mapped']}")
        else:
            print("   ❌ Failed to parse test failure")
            return False
        
        # Test 2: Read source code
        print("2. Testing source code reading...")
        source_content = tools._read_source_code_internal("backend/routers/tasks.py")
        if "def read_tasks" in source_content:
            print("   ✅ Successfully read source code")
        else:
            print("   ❌ Failed to read source code")
            return False
        
        # Test 3: Test tool setup
        print("3. Testing tool setup...")
        tool_names = [tool.name for tool in tools.get_all_tools()]
        expected_tools = ["read_source_code", "apply_code_fix", "read_test_results", "run_fresh_tests"]
        
        missing_tools = []
        for expected in expected_tools:
            if expected not in tool_names:
                missing_tools.append(expected)
        
        if missing_tools:
            print(f"   ❌ Missing tools: {missing_tools}")
            return False
        else:
            print(f"   ✅ All expected tools available: {tool_names}")
        
        return True

if __name__ == "__main__":
    print("Testing debug agent tools...")
    success = test_debug_tools()
    if success:
        print("✅ All tests passed - debug agent tools are working correctly")
    else:
        print("❌ Some tests failed - debug agent tools need fixes")
    
    sys.exit(0 if success else 1)
