#!/usr/bin/env python3
"""
Test script to verify the debug agent parsing functionality
"""

import os
import sys
import tempfile

# Add the src path to import our debug agent
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'main_deploy'))

from debug_agent import DebuggingTools

def test_parse_test_log():
    """Test the improved test log parsing"""
    
    # Create a temporary test log with pytest-style output
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
    
    # Create temporary directory and file
    with tempfile.TemporaryDirectory() as temp_dir:
        test_log_path = os.path.join(temp_dir, "test_results.log")
        
        with open(test_log_path, 'w') as f:
            f.write(test_log_content)
        
        # Create debug tools instance
        tools = DebuggingTools(project_root=temp_dir)
        
        # Test parsing
        failure = tools._parse_test_log_file(test_log_path)
        
        print("Parsed failure:")
        if failure:
            for key, value in failure.items():
                print(f"  {key}: {value}")
            
            # Validate key fields
            expected_function = "read_tasks"
            expected_error_content = "assert 0 == 2"
            
            success = True
            if failure.get("source_function_mapped") != expected_function:
                print(f"  ❌ Expected function '{expected_function}', got '{failure.get('source_function_mapped')}'")
                success = False
            else:
                print(f"  ✅ Correctly mapped to function '{expected_function}'")
            
            if expected_error_content not in failure.get("error_summary_line", ""):
                print(f"  ❌ Expected error content '{expected_error_content}' not found")
                success = False
            else:
                print(f"  ✅ Correctly extracted assertion error")
            
            return success
        else:
            print("  No failure parsed")
            return False

if __name__ == "__main__":
    print("Testing debug agent parsing functionality...")
    success = test_parse_test_log()
    if success:
        print("✅ Test passed - debug agent can parse test failures")
    else:
        print("❌ Test failed - debug agent could not parse test failures")
    
    sys.exit(0 if success else 1)
