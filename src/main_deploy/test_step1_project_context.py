#!/usr/bin/env python3
"""
Test script for ProjectContext class - Step 1
"""

import os
import sys

# Add the src path to import our coding agent
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'main_deploy'))

from coding_agent import ProjectContext

def test_project_context():
    """Test the ProjectContext class functionality"""
    
    print("Testing ProjectContext class...")
    
    # Test 1: Basic initialization
    print("1. Testing initialization...")
    context = ProjectContext("TestProject", "FastAPI")
    
    assert context.project_name == "TestProject"
    assert context.tech_stack == "fastapi"
    assert isinstance(context.defined_classes, dict)
    assert isinstance(context.database_models, list)
    print("   ✅ Initialization successful")
    
    # Test 2: Class registration
    print("2. Testing class registration...")
    context.register_class("Task", "models.py", is_database_model=True)
    context.register_class("UserService", "services.py", is_database_model=False)
    
    assert "Task" in context.defined_classes
    assert context.defined_classes["Task"] == "models.py"
    assert "Task" in context.database_models
    assert "UserService" not in context.database_models
    print("   ✅ Class registration working")
    
    # Test 3: Function registration
    print("3. Testing function registration...")
    context.register_function("create_task", "crud.py")
    context.register_function("get_db", "database.py")
    
    assert "create_task" in context.defined_functions
    assert context.defined_functions["get_db"] == "database.py"
    print("   ✅ Function registration working")
    
    # Test 4: Import tracking
    print("4. Testing import tracking...")
    context.register_import("routes.py", "from models import Task")
    context.register_import("routes.py", "from database import get_db")
    
    assert "routes.py" in context.imports_used
    assert len(context.imports_used["routes.py"]) == 2
    print("   ✅ Import tracking working")
    
    # Test 5: Forbidden redefinitions
    print("5. Testing forbidden redefinitions...")
    forbidden = context.get_forbidden_redefinitions("routes.py")
    
    assert any("class Task" in item for item in forbidden)
    assert any("class UserService" in item for item in forbidden)
    print("   ✅ Forbidden redefinitions detection working")
    
    # Test 6: Required imports
    print("6. Testing required imports...")
    required = context.get_required_imports("models.py")
    
    # Should suggest importing Base from database for models.py
    assert any("from database import Base" in imp for imp in required)
    print("   ✅ Required imports suggestions working")
    
    # Test 7: Code analysis
    print("7. Testing code analysis...")
    sample_code = """
from database import Base
from sqlalchemy import Column, Integer, String

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)

def get_user_by_id(user_id: int):
    return None
    """
    
    context.update_from_generated_file("models.py", sample_code)
    
    assert "User" in context.defined_classes
    assert "get_user_by_id" in context.defined_functions
    print("   ✅ Code analysis working")
    
    # Test 8: Context summary
    print("8. Testing context summary...")
    summary = context.get_context_summary()
    
    assert "TestProject" in summary
    assert "fastapi" in summary
    assert "Task" in summary
    assert "User" in summary
    print("   ✅ Context summary generation working")
    
    return True

if __name__ == "__main__":
    print("Testing ProjectContext class...")
    success = test_project_context()
    
    if success:
        print("✅ All ProjectContext tests passed!")
        print("\nStep 1 complete. ProjectContext class is working correctly.")
    else:
        print("❌ Some tests failed")
    
    sys.exit(0 if success else 1)
