"""
Test the validation and auto-fix functionality
"""
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'main_deploy'))

from coding_agent import ProjectContext, CodeValidator, ContentClassifier, ImportAnalyzer, AutoFixer

def test_schema_model_confusion():
    """Test detection and auto-fix of schema/model import confusion"""
    
    print("🧪 Testing Schema/Model Import Confusion Detection")
    print("=" * 60)
    
    # Create a mock project context
    project_context = ProjectContext("test_project", "fastapi")
    
    # Simulate project structure
    project_context.project_structure['database_files'] = ['backend/database.py']
    project_context.project_structure['model_files'] = ['backend/models.py', 'backend/schemas.py']
    project_context.project_structure['route_files'] = ['backend/routes.py']
    
    # Register some classes to simulate context
    project_context.register_class("Task", "backend/models.py", is_database_model=True)
    project_context.register_class("TaskCreate", "backend/schemas.py", is_database_model=False)
    project_context.register_class("TaskUpdate", "backend/schemas.py", is_database_model=False)
    
    # Problematic code with schema/model confusion
    problematic_code = """
from backend.models import TaskCreate, TaskUpdate, Task
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

def get_db():
    pass

@router.post("/tasks/")
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    # This should work after auto-fix
    db_task = Task(title=task.title, description=task.description)
    db.add(db_task)
    db.commit()
    return db_task

@router.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate, db: Session = Depends(get_db)):
    # This should also work after auto-fix
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    for field, value in task.dict(exclude_unset=True).items():
        setattr(db_task, field, value)
    
    db.commit()
    return db_task
"""
    
    # Test the validation system
    validator = CodeValidator(project_context)
    result = validator.validate_and_fix_generated_code("backend/routes.py", problematic_code)
    
    print(f"✅ Validation Results:")
    print(f"   Is Valid: {result['is_valid']}")
    print(f"   Issues Found: {len(result['issues_found'])}")
    print(f"   Fixes Applied: {len(result['fixes_applied'])}")
    
    if result['issues_found']:
        print(f"\n🔍 Issues Detected:")
        for issue in result['issues_found']:
            print(f"   - {issue}")
    
    if result['fixes_applied']:
        print(f"\n🔧 Auto-Fixes Applied:")
        for fix in result['fixes_applied']:
            print(f"   - {fix['action']}: {fix.get('reason', 'N/A')}")
    
    if result['fixed_code'] != problematic_code:
        print(f"\n📝 Code was automatically fixed!")
        print("=" * 40)
        print("FIXED CODE:")
        print("=" * 40)
        print(result['fixed_code'])
        print("=" * 40)
    else:
        print(f"\n📝 No changes were made to the code")
    
    print(f"\n📋 Validation Summary:")
    print(result['validation_summary'])
    
    return result

def test_content_classification():
    """Test content classification functionality"""
    
    print("\n🧪 Testing Content Classification")
    print("=" * 60)
    
    # Test schema file classification
    schema_code = """
from pydantic import BaseModel
from typing import Optional

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(TaskBase):
    title: Optional[str] = None

class Task(TaskBase):
    id: int
    
    class Config:
        orm_mode = True
"""
    
    # Test model file classification
    model_code = """
from sqlalchemy import Column, Integer, String, Text
from .database import Base

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
"""
    
    classifier = ContentClassifier()
    
    # Test schema classification
    schema_result = classifier.classify_file_content("backend/schemas.py", schema_code)
    print(f"Schema file classification:")
    print(f"   Content Type: {schema_result['content_type']}")
    print(f"   Contains Pydantic: {schema_result['contains_pydantic']}")
    print(f"   Schema Classes: {schema_result['schema_classes']}")
    print(f"   Model Classes: {schema_result['model_classes']}")
    
    # Test model classification
    model_result = classifier.classify_file_content("backend/models.py", model_code)
    print(f"\nModel file classification:")
    print(f"   Content Type: {model_result['content_type']}")
    print(f"   Contains SQLAlchemy: {model_result['contains_sqlalchemy']}")
    print(f"   Schema Classes: {model_result['schema_classes']}")
    print(f"   Model Classes: {model_result['model_classes']}")
    
    return schema_result, model_result

if __name__ == "__main__":
    print("🚀 Testing Code Validation and Auto-Fix System")
    print("=" * 80)
    
    try:
        # Test content classification first
        test_content_classification()
        
        # Test the main validation and auto-fix functionality
        result = test_schema_model_confusion()
        
        print(f"\n🎉 Test completed successfully!")
        print(f"Validation system is {'working correctly' if result['fixes_applied'] else 'not detecting issues as expected'}")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
