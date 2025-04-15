"""
This module contains controller functions that coordinate between models and views.
"""

import streamlit as st
from datetime import datetime

from .models import SpecificationGenerator
from .utils import save_to_json, get_timestamp_filename, load_json_file

class SpecificationController:
    """
    Controller class for managing specification generation and handling.
    """
    
    def __init__(self):
        """Initialize the specification controller."""
        self.generator = SpecificationGenerator()
    
    def generate_specification(self, user_description, custom_prompt=None):
        """
        Generate a specification based on user description.
        
        Args:
            user_description (str): The user's description of the software requirements.
            custom_prompt (str, optional): A custom prompt template. Defaults to None.
            
        Returns:
            tuple: A tuple containing (success, result, filepath or error message).
        """
        if not user_description:
            return False, None, "Please enter a description of your software requirements."
        
        try:
            # Generate the specification
            spec_data = self.generator.generate_spec(user_description, custom_prompt)
            
            if not spec_data:
                return False, None, "Failed to generate specification."
            
            # Save to JSON file
            project_name = spec_data.get("project_name", "unnamed_project")
            filename = get_timestamp_filename(project_name=project_name)
            filepath = save_to_json(spec_data, filename)
            
            # Create success message
            if "metadata" in spec_data and "auto_clarification" in spec_data["metadata"]:
                auto_clarify = spec_data["metadata"]["auto_clarification"]
                assumptions_clarified = auto_clarify.get("assumptions_clarified", 0)
                questions_answered = auto_clarify.get("questions_answered", 0)
                
                message = f"Specification generated and saved to {filepath}. Automatically clarified {assumptions_clarified} assumptions and answered {questions_answered} questions."
            else:
                message = f"Specification generated and saved to {filepath}"
            
            return True, spec_data, message
            
        except Exception as e:
            return False, None, f"Error generating specification: {str(e)}"
    
    def load_specification(self, filepath):
        """
        Load a specification from a file.
        
        Args:
            filepath (str): The path to the specification file.
            
        Returns:
            tuple: A tuple containing (success, loaded data, message).
        """
        try:
            file_data = load_json_file(filepath)
            return True, file_data, f"Loaded specification from {filepath}"
        except Exception as e:
            return False, None, f"Error loading specification: {str(e)}"
    
    def export_to_markdown(self, spec_data):
        """
        Export specification data to markdown format.
        
        Args:
            spec_data (dict): The specification data.
            
        Returns:
            str: The markdown content.
        """
        if "project_name" not in spec_data:
            return "# Unnamed Project\n\n"
            
        markdown_content = f"# {spec_data['project_name']}\n\n"
        markdown_content += f"## Overview\n{spec_data.get('overview', 'N/A')}\n\n"
        
        # Add functional requirements
        if "functional_requirements" in spec_data:
            markdown_content += "## Functional Requirements\n\n"
            for req in spec_data["functional_requirements"]:
                markdown_content += f"### {req.get('id')} - {req.get('title')}\n"
                markdown_content += f"- Description: {req.get('description')}\n"
                markdown_content += f"- Priority: {req.get('priority')}\n\n"
                
                if "acceptance_criteria" in req and req["acceptance_criteria"]:
                    markdown_content += "#### Acceptance Criteria\n"
                    for ac in req["acceptance_criteria"]:
                        markdown_content += f"- {ac}\n"
                    markdown_content += "\n"
        
        # Add non-functional requirements
        if "non_functional_requirements" in spec_data:
            markdown_content += "## Non-Functional Requirements\n\n"
            for req in spec_data["non_functional_requirements"]:
                markdown_content += f"### {req.get('id')} - {req.get('category')}\n"
                markdown_content += f"- Description: {req.get('description')}\n"
                if "constraints" in req:
                    markdown_content += f"- Constraints: {req.get('constraints')}\n"
                markdown_content += "\n"
        
        # Add data entities
        if "data_entities" in spec_data:
            markdown_content += "## Data Entities\n\n"
            for entity in spec_data["data_entities"]:
                markdown_content += f"### {entity.get('name')}\n\n"
                
                if "attributes" in entity and entity["attributes"]:
                    markdown_content += "#### Attributes\n\n"
                    for attr in entity["attributes"]:
                        markdown_content += f"- **{attr.get('name')}** ({attr.get('type')}): {attr.get('description')}\n"
                    markdown_content += "\n"
                
                if "relationships" in entity and entity["relationships"]:
                    markdown_content += "#### Relationships\n\n"
                    for rel in entity["relationships"]:
                        markdown_content += f"- {rel}\n"
                    markdown_content += "\n"
        
        # Add API endpoints
        if "api_endpoints" in spec_data:
            markdown_content += "## API Endpoints\n\n"
            for endpoint in spec_data["api_endpoints"]:
                markdown_content += f"### {endpoint.get('method')} {endpoint.get('path')}\n\n"
                markdown_content += f"Description: {endpoint.get('description')}\n\n"
                
                if "request_parameters" in endpoint and endpoint["request_parameters"]:
                    markdown_content += "#### Request Parameters\n\n"
                    for param in endpoint["request_parameters"]:
                        required = "Required" if param.get("required", False) else "Optional"
                        markdown_content += f"- **{param.get('name')}** ({param.get('type')}, {required}): {param.get('description')}\n"
                    markdown_content += "\n"
                
                if "response" in endpoint:
                    markdown_content += "#### Response\n\n"
                    if "success" in endpoint["response"]:
                        markdown_content += f"- **Success**: {endpoint['response']['success']}\n"
                    if "error" in endpoint["response"]:
                        markdown_content += f"- **Error**: {endpoint['response']['error']}\n"
                    markdown_content += "\n"
        
        # Add assumptions
        if "assumptions" in spec_data and spec_data["assumptions"]:
            markdown_content += "## Assumptions\n\n"
            for assumption in spec_data["assumptions"]:
                markdown_content += f"- {assumption}\n"
            markdown_content += "\n"
        
        # Add open questions
        if "open_questions" in spec_data and spec_data["open_questions"]:
            markdown_content += "## Open Questions\n\n"
            for question in spec_data["open_questions"]:
                markdown_content += f"- {question}\n"
            markdown_content += "\n"
        
        # Add resolved questions
        if "resolved_questions" in spec_data and spec_data["resolved_questions"]:
            markdown_content += "## Automatically Resolved Questions\n\n"
            for item in spec_data["resolved_questions"]:
                markdown_content += f"**Q:** {item['question']}\n"
                markdown_content += f"**A:** {item['answer']} (Confidence: {item.get('confidence', 'Medium')})\n\n"
        
        return markdown_content
