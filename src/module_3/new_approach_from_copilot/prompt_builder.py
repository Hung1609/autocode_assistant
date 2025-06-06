from typing import Dict, Any
import json

class PromptBuilder:
    """Builds prompts for different file types and frameworks"""
    
    def __init__(self):
        self.base_instructions = """
        CONTEXT:
        - You are an expert Senior Software Engineer acting as a meticulous code writer.
        - Your task is to generate complete, syntactically correct code for the specified file.
        - Base your implementation on the provided JSON design and specification files.
        
        INSTRUCTIONS FOR CODE GENERATION:
        1. Output Code Only - No explanations, comments outside code, or markdown formatting.
        2. Ensure the code aligns with the JSON Design and Specification.
        3. Include necessary imports and follow framework conventions.
        4. Generate complete, ready-to-run code.
        """
    
    def build_prompt(self, file_path: str, json_design: Dict, json_spec: Dict, 
                    plan: Dict, framework: str = 'fastapi') -> str:
        """Build a prompt for generating code for a specific file"""
        
        project_name = json_spec.get('project_Overview', {}).get('project_Name', 'Application')
        tech_stack = json_spec.get('technology_Stack', {})
        backend_info = tech_stack.get('backend', {})
        frontend_info = tech_stack.get('frontend', {})
        
        # Determine file type and role
        file_role = self._determine_file_role(file_path, plan)
        
        # Build framework-specific instructions
        framework_instructions = self._get_framework_instructions(framework, file_role, plan)
        
        prompt = f"""
        {self.base_instructions}
        
        PROJECT INFORMATION:
        - Project Name: {project_name}
        - Backend: {backend_info.get('language', 'Python')} with {backend_info.get('framework', 'FastAPI')}
        - Frontend: {frontend_info.get('language', 'HTML/CSS/JS')} with {frontend_info.get('framework', 'Vanilla')}
        - Storage: {json_design.get('data_Design', {}).get('storage_Type', 'SQLite')}
        
        TARGET FILE INFORMATION:
        - File Path: {file_path}
        - File Role: {file_role}
        - Project Root: {plan.get('project_root_directory', '')}
        - Backend Module: {plan.get('backend_module_path', '')}
        - Frontend Directory: {plan.get('frontend_dir', '')}
        
        {framework_instructions}
        
        JSON DESIGN:
        ```json
        {json.dumps(json_design, indent=2)}
        ```
        
        JSON SPECIFICATION:
        ```json
        {json.dumps(json_spec, indent=2)}
        ```
        
        Generate the complete code for: {file_path}
        """
        
        return prompt.strip()
    
    def _determine_file_role(self, file_path: str, plan: Dict) -> str:
        """Determine the role of a file based on its path"""
        import os
        
        filename = os.path.basename(file_path)
        relative_path = file_path.replace(plan.get('project_root_directory', ''), '').lstrip('\\/')
        
        # Special files
        if filename == 'requirements.txt':
            return 'dependencies'
        elif filename.endswith('.bat') or filename.endswith('.sh'):
            return 'startup_script'
        elif filename == '.env':
            return 'environment_config'
        elif filename == 'main.py' or filename == 'app.py':
            return 'main_application'
        elif 'model' in filename.lower():
            return 'data_model'
        elif 'route' in filename.lower() or 'api' in filename.lower():
            return 'api_endpoint'
        elif filename.endswith('.html'):
            return 'frontend_template'
        elif filename.endswith('.css'):
            return 'stylesheet'
        elif filename.endswith('.js'):
            return 'frontend_script'
        elif 'test' in filename.lower():
            return 'test_file'
        else:
            return 'utility_module'
    
    def _get_framework_instructions(self, framework: str, file_role: str, plan: Dict) -> str:
        """Get framework-specific instructions for different file roles"""
        
        instructions = {
            'fastapi': {
                'main_application': f"""
                FASTAPI MAIN APPLICATION INSTRUCTIONS:
                - Import FastAPI, logging, and necessary middleware
                - Set up advanced JSON logging with request ID correlation using contextvars
                - Configure RotatingFileHandler for logs/app.log
                - Create RequestIDMiddleware for request tracing
                - Initialize FastAPI app with proper metadata
                - Add health check endpoint
                - Mount static files at the end: app.mount("/", StaticFiles(directory="{plan.get('frontend_dir', 'frontend')}", html=True), name="static")
                - Include if __name__ == "__main__": uvicorn.run() block
                """,
                'data_model': """
                DATA MODEL INSTRUCTIONS:
                - Use SQLAlchemy for ORM models
                - Use Pydantic for request/response models
                - Include proper field validation
                - Add logging for CRUD operations
                """,
                'api_endpoint': """
                API ENDPOINT INSTRUCTIONS:
                - Use FastAPI router patterns
                - Include proper HTTP status codes
                - Add request/response logging
                - Use dependency injection where appropriate
                - Include error handling with HTTPException
                """
            },
            'flask': {
                'main_application': f"""
                FLASK MAIN APPLICATION INSTRUCTIONS:
                - Import Flask and necessary extensions
                - Set up logging configuration
                - Configure Flask app with proper settings
                - Add CORS support
                - Create routes for serving static files from {plan.get('frontend_dir', 'frontend')}
                - Include health check route
                - Add if __name__ == '__main__': app.run() block
                """,
                'data_model': """
                DATA MODEL INSTRUCTIONS:
                - Use Flask-SQLAlchemy for ORM models
                - Include proper relationships and constraints
                - Add validation methods
                """,
                'api_endpoint': """
                API ENDPOINT INSTRUCTIONS:
                - Use Flask blueprints for organization
                - Include proper error handling
                - Return JSON responses
                - Add request logging
                """
            }
        }
        
        framework_lower = framework.lower()
        if framework_lower in instructions and file_role in instructions[framework_lower]:
            return instructions[framework_lower][file_role]
        
        return "Follow standard coding practices for this file type."

# Global prompt builder instance
prompt_builder = PromptBuilder()
