#!/usr/bin/env python3
"""
Test script for the new dynamic ProjectContext implementation.
"""

import json
import sys
import os

# Add the current directory to path to import coding_agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from coding_agent import ProjectContext

def test_project_context():
    """Test the new ProjectContext with a sample project structure"""
    
    # Sample design data mimicking a typical web app structure
    sample_design = {
        "folder_Structure": {
            "root_Project_Directory_Name": "sample_webapp",
            "structure": [
                {"path": "backend", "description": "Backend directory"},
                {"path": "backend/database.py", "description": "Database configuration and connection"},
                {"path": "backend/models.py", "description": "SQLAlchemy data models"},
                {"path": "backend/routes.py", "description": "API routes and endpoints"},
                {"path": "backend/main.py", "description": "Main FastAPI application entry point"},
                {"path": "frontend", "description": "Frontend directory"},
                {"path": "frontend/index.html", "description": "Main HTML page"},
                {"path": "frontend/style.css", "description": "CSS styles"},
                {"path": "frontend/script.js", "description": "Frontend JavaScript"},
                {"path": "requirements.txt", "description": "Python dependencies"},
                {"path": ".env", "description": "Environment configuration"}
            ]
        }
    }
    
    print("🧪 Testing ProjectContext with sample structure...")
    print(f"Project structure: {len(sample_design['folder_Structure']['structure'])} items")
    
    # Initialize ProjectContext
    context = ProjectContext(
        project_name="sample_webapp",
        tech_stack="fastapi",
        design_data=sample_design
    )
    
    print("\n📊 Project Structure Analysis:")
    structure = context.project_structure
    for key, value in structure.items():
        if isinstance(value, list) and value:
            print(f"  {key}: {value}")
        elif isinstance(value, dict) and value:
            print(f"  {key}: {len(value)} items")
    
    print("\n🔗 Dynamic Framework Patterns:")
    patterns = context.established_patterns
    print(json.dumps(patterns, indent=2))
    
    print("\n📝 Context for specific files:")
    
    # Test context for database file
    if context.project_structure['database_files']:
        db_file = context.project_structure['database_files'][0]
        print(f"\n📁 Database file ({db_file}):")
        db_context = context.get_generation_context_for_file(db_file)
        print(f"  Type: {db_context['file_type']}")
        print(f"  Dependencies: {db_context['dependencies']}")
        print(f"  Forbidden: {db_context['forbidden_redefinitions']}")
        
        print("\n🎯 Context instructions for database file:")
        print(context.get_context_for_prompt(db_file))
    
    # Test context for models file
    if context.project_structure['model_files']:
        model_file = context.project_structure['model_files'][0]
        print(f"\n📁 Model file ({model_file}):")
        model_context = context.get_generation_context_for_file(model_file)
        print(f"  Type: {model_context['file_type']}")
        print(f"  Dependencies: {model_context['dependencies']}")
        print(f"  Forbidden: {model_context['forbidden_redefinitions']}")
        
        print("\n🎯 Context instructions for model file:")
        print(context.get_context_for_prompt(model_file))
    
    # Test context for entry point
    if context.project_structure['entry_points']:
        entry_file = context.project_structure['entry_points'][0]
        print(f"\n📁 Entry point ({entry_file}):")
        entry_context = context.get_generation_context_for_file(entry_file)
        print(f"  Type: {entry_context['file_type']}")
        print(f"  Dependencies: {entry_context['dependencies']}")
        print(f"  Forbidden: {entry_context['forbidden_redefinitions']}")
        
        print("\n🎯 Context instructions for entry point:")
        print(context.get_context_for_prompt(entry_file))
    
    print("\n✅ ProjectContext test completed successfully!")
    print("\nKey improvements over hardcoded approach:")
    print("  ✓ Dynamic structure analysis based on actual files")
    print("  ✓ Context-aware import patterns")
    print("  ✓ File-specific generation instructions")
    print("  ✓ Dependency-based generation order")
    print("  ✓ Shared definition conflict prevention")

if __name__ == "__main__":
    test_project_context()
