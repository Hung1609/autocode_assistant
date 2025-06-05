from abc import ABC, abstractmethod
from typing import Dict, Any, List
import json
import logging

# Initialize logger for this module
logger = logging.getLogger(__name__)

class FrameworkTemplate(ABC):
    """Abstract base class for framework-specific code generation templates"""
    
    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """Get framework-specific dependencies"""
        pass
    
    @abstractmethod
    def generate_main_file_content(self, plan: Dict[str, Any], json_design: Dict, json_spec: Dict) -> str:
        """Generate main application file content"""
        pass
    
    @abstractmethod
    def get_run_command(self, backend_module_path: str) -> str:
        """Get command to run the application"""
        pass
    
    @abstractmethod
    def get_file_extensions(self) -> Dict[str, str]:
        """Get file extensions for this framework"""
        pass

class FastAPITemplate(FrameworkTemplate):
    """FastAPI framework template"""
    
    def get_dependencies(self) -> List[str]:
        return ['fastapi[all]', 'uvicorn[standard]', 'sqlalchemy', 'pydantic']
    
    def generate_main_file_content(self, plan: Dict[str, Any], json_design: Dict, json_spec: Dict) -> str:
        return f"""
import logging
import logging.handlers
import json
import contextvars
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Request ID context variable
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar('request_id')

# Custom JSON formatter
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {{
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger_name': record.name,
            'message': record.getMessage(),
            'pathname': record.pathname,
            'funcName': record.funcName,
            'lineno': record.lineno,
            'request_id': getattr(record, 'request_id', None)
        }}
        
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

# Request ID middleware
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
            return response
        finally:
            request_id_ctx.reset(token)

# Logging filter to add request ID
class RequestIDFilter(logging.Filter):
    def filter(self, record):
        try:
            record.request_id = request_id_ctx.get()
        except LookupError:
            record.request_id = None
        return True

# Configure logging
def setup_logging():
    # Create logs directory
    import os
    os.makedirs('logs', exist_ok=True)
    
    # JSON formatter for file
    json_formatter = JSONFormatter()
    
    # Human readable formatter for console
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        'logs/app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(json_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler, console_handler]
    )
    
    # Add request ID filter
    logger = logging.getLogger()
    logger.addFilter(RequestIDFilter())

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="{json_spec.get('project_Overview', {}).get('project_Name', 'Generated Application')}",
    description="{json_spec.get('project_Overview', {}).get('project_Purpose', 'Auto-generated application')}",
    version="1.0.0"
)

# Add middleware
app.add_middleware(RequestIDMiddleware)

# Health check endpoint
@app.get("/health")
async def health_check():
    logger.info("Health check requested")
    return {{"status": "healthy", "timestamp": datetime.now().isoformat()}}

# Add your API routes here
# TODO: Implement API endpoints based on interface_Design

# Mount static files (must be last)
app.mount("/", StaticFiles(directory="{plan['frontend_dir']}", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting application directly")
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
"""
    
    def get_run_command(self, backend_module_path: str) -> str:
        return f'python -m uvicorn {backend_module_path}:app --reload --port 8001'
    
    def get_file_extensions(self) -> Dict[str, str]:
        return {
            'main': '.py',
            'model': '.py',
            'router': '.py',
            'service': '.py'
        }

class FlaskTemplate(FrameworkTemplate):
    """Flask framework template"""
    
    def get_dependencies(self) -> List[str]:
        return ['flask', 'flask-sqlalchemy', 'flask-wtf', 'flask-cors']
    
    def generate_main_file_content(self, plan: Dict[str, Any], json_design: Dict, json_spec: Dict) -> str:
        return f"""
import logging
import logging.handlers
import json
import os
from flask import Flask, send_from_directory
from flask_cors import CORS

# Configure logging
def setup_logging():
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[
            logging.handlers.RotatingFileHandler(
                'logs/app.log',
                maxBytes=10*1024*1024,
                backupCount=5
            ),
            logging.StreamHandler()
        ]
    )

setup_logging()
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Enable CORS
CORS(app)

# Health check route
@app.route('/health')
def health_check():
    logger.info("Health check requested")
    return {{"status": "healthy"}}

# Serve static files
@app.route('/')
def serve_frontend():
    return send_from_directory('{plan['frontend_dir']}', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('{plan['frontend_dir']}', path)

# Add your API routes here
# TODO: Implement API endpoints based on interface_Design

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(host='0.0.0.0', port=8001, debug=True)
"""
    
    def get_run_command(self, backend_module_path: str) -> str:
        return f'python -m flask --app {backend_module_path} run --port 8001'
    
    def get_file_extensions(self) -> Dict[str, str]:
        return {
            'main': '.py',
            'model': '.py',
            'route': '.py',
            'service': '.py'
        }

class TemplateManager:
    """Manages framework templates"""
    
    def __init__(self):
        self.templates = {
            'fastapi': FastAPITemplate(),
            'flask': FlaskTemplate()
        }
    
    def get_template(self, framework: str) -> FrameworkTemplate:
        """Get template for specified framework"""
        framework_lower = framework.lower()
        if framework_lower not in self.templates:
            # Default to FastAPI if framework not found
            logger.warning(f"Framework '{framework}' not supported, defaulting to FastAPI")
            framework_lower = 'fastapi'
        return self.templates[framework_lower]
    
    def register_template(self, name: str, template: FrameworkTemplate):
        """Register a new framework template"""
        self.templates[name.lower()] = template

# Global template manager instance
template_manager = TemplateManager()
