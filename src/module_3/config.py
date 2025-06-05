import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from platform_config import platform_config

@dataclass
class CodingAgentConfig:
    """Configuration for the coding agent"""
    
    # Paths
    outputs_dir: str = field(default_factory=lambda: os.path.join(os.getcwd(), 'outputs'))
    base_output_dir: str = 'code_generated_result'
    python_path: str = field(default_factory=lambda: platform_config.get_python_executable())
    
    # LLM Settings
    default_model: str = 'gemini-2.0-flash'
    api_call_delay_seconds: int = 5
    
    # Framework Templates
    framework_templates: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        'fastapi': {
            'dependencies': ['fastapi[all]', 'uvicorn[standard]', 'sqlalchemy', 'pydantic'],
            'main_file': 'main.py',
            'run_command': 'python -m uvicorn {module}:app --reload --port 8001'
        },
        'flask': {
            'dependencies': ['flask', 'flask-sqlalchemy', 'flask-wtf'],
            'main_file': 'app.py',
            'run_command': 'python -m flask --app {module} run --port 8001'
        },
        'django': {
            'dependencies': ['django', 'djangorestframework'],
            'main_file': 'manage.py',
            'run_command': 'python manage.py runserver 8001'
        }
    })
    
    # Default file contents
    default_env_content: str = "DATABASE_URL=sqlite:///app.db\nSECRET_KEY=your-secret-key-here\n"
    
    @classmethod
    def load_from_file(cls, config_path: str) -> 'CodingAgentConfig':
        """Load configuration from JSON file"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            return cls(**config_data)
        return cls()
    
    def save_to_file(self, config_path: str):
        """Save configuration to JSON file"""
        config_dict = {
            'outputs_dir': self.outputs_dir,
            'base_output_dir': self.base_output_dir,
            'python_path': self.python_path,
            'default_model': self.default_model,
            'api_call_delay_seconds': self.api_call_delay_seconds,
            'framework_templates': self.framework_templates,
            'default_env_content': self.default_env_content
        }
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2)
    
    def get_framework_config(self, framework: str) -> Dict[str, Any]:
        """Get configuration for a specific framework"""
        return self.framework_templates.get(framework.lower(), self.framework_templates['fastapi'])
    
    def auto_detect_paths(self):
        """Auto-detect common paths based on current environment"""
        # Try to find outputs directory
        current_dir = Path.cwd()
        possible_outputs = [
            current_dir / 'outputs',
            current_dir / 'src' / 'module_1_vs_2' / 'outputs',
            current_dir.parent / 'outputs'
        ]
        
        for path in possible_outputs:
            if path.exists():
                self.outputs_dir = str(path)
                break

# Global configuration instance
config = CodingAgentConfig()
config.auto_detect_paths()
