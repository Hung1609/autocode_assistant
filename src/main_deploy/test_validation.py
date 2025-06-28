"""
Test script to validate the import error prevention and auto-fix functionality
"""
import sys
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'main_deploy'))

from coding_agent import ProjectContext, CodeValidator, ContentClassifier, ImportAnalyzer, AutoFixer

def test_import_error_detection_and_fix():
    """Test the validation system with problematic code"""
    
    # Sample problematic code that has schema/model confusion
    problematic_code = """
from backend.models import TaskCreate
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

router = APIRouter()

@router.post("/tasks/")
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    # This should fail because TaskCreate is a Pydantic schema, not a SQLAlchemy model
    db_task = Task(title=task.title, description=task.description)
    db.add(db_task)
    db.commit()
    return db_task
"""

    # Initialize project context
    project_context = ProjectContext("test_project", "fastapi")
    
    # Simulate some existing context
    project_context.register_class("Task", "backend/models.py", is_database_model=True)
    project_context.register_class("TaskCreate", "backend/schemas.py", is_database_model=False)
    
    # Initialize validator
    validator = CodeValidator(project_context)
    
    print("🧪 Testing import error detection and auto-fix...")
    print("=" * 60)
    
    # Test the validation
    result = validator.validate_and_fix_generated_code("backend/routes.py", problematic_code)
    
    print(f"✅ Validation Complete!")
    print(f"Is Valid: {result['is_valid']}")
    print(f"Issues Found: {len(result['issues_found'])}")
    print(f"Fixes Applied: {len(result['fixes_applied'])}")
    
    if result['issues_found']:
        print("\n🔍 Issues Found:")
        for issue in result['issues_found']:
            print(f"  - {issue}")
    
    if result['fixes_applied']:
        print("\n🔧 Fixes Applied:")
        for fix in result['fixes_applied']:
            print(f"  - {fix['action']}: {fix.get('reason', 'No reason provided')}")
    
    print(f"\n📋 Validation Summary:")
    print(result['validation_summary'])
    
    if result['fixed_code'] != problematic_code:
        print(f"\n📝 Fixed Code:")
        print("-" * 40)
        print(result['fixed_code'])
        print("-" * 40)
    else:
        print(f"\n📝 No code changes were made")
    
    return result

def test_content_classification():
    """Test the content classification system"""
    
    print("\n🧪 Testing content classification...")
    print("=" * 60)
    
    # Sample model file
    model_code = """
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
"""

    # Sample schema file
    schema_code = """
from pydantic import BaseModel
from typing import Optional

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int
    
    class Config:
        orm_mode = True
"""

    classifier = ContentClassifier()
    
    # Test model classification
    model_result = classifier.classify_file_content("backend/models.py", model_code)
    print(f"Model file classification: {model_result}")
    
    # Test schema classification
    schema_result = classifier.classify_file_content("backend/schemas.py", schema_code)
    print(f"Schema file classification: {schema_result}")
    
    return model_result, schema_result

def test_import_analysis():
    """Test import analysis functionality"""
    
    print("\n🧪 Testing import analysis...")
    print("=" * 60)
    
    # Sample code with mixed imports
    test_code = """
from backend.models import TaskCreate  # Wrong - TaskCreate is a schema
from backend.schemas import Task       # Wrong - Task model should come from models
from sqlalchemy.orm import Session
from fastapi import APIRouter

router = APIRouter()

def get_task(task_id: int, db: Session):
    return db.query(Task).filter(Task.id == task_id).first()
"""

    # Setup project context
    project_context = ProjectContext("test_project", "fastapi")
    project_context.register_class("Task", "backend/models.py", is_database_model=True)
    project_context.register_class("TaskCreate", "backend/schemas.py", is_database_model=False)
    
    analyzer = ImportAnalyzer(project_context)
    classifier = ContentClassifier()
    
    # Classify the file
    classification = classifier.classify_file_content("backend/routes.py", test_code)
    
    # Analyze imports
    analysis = analyzer.analyze_imports("backend/routes.py", test_code, classification)
    
    print(f"Import analysis results:")
    print(f"  - Valid imports: {len(analysis['valid_imports'])}")
    print(f"  - Invalid imports: {len(analysis['invalid_imports'])}")
    print(f"  - Missing imports: {len(analysis['missing_imports'])}")
    print(f"  - Auto-fix suggestions: {len(analysis['auto_fix_suggestions'])}")
    
    if analysis['invalid_imports']:
        print(f"\n❌ Invalid imports found:")
        for invalid in analysis['invalid_imports']:
            print(f"  - {invalid}")
    
    if analysis['auto_fix_suggestions']:
        print(f"\n🔧 Auto-fix suggestions:")
        for suggestion in analysis['auto_fix_suggestions']:
            print(f"  - {suggestion}")
    
    return analysis

if __name__ == "__main__":
    print("🚀 Starting Validation System Tests")
    print("=" * 80)
    
    try:
        # Test content classification
        test_content_classification()
        
        # Test import analysis  
        test_import_analysis()
        
        # Test full validation and auto-fix
        test_import_error_detection_and_fix()
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
