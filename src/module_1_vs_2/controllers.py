# Control models and views.

from datetime import datetime
from models import SpecificationGenerator
from utils import save_data_to_json_file, get_filename, load_json_file

class SpecificationController:
    def __init__(self):
        self.generator = SpecificationGenerator()
    
    def generate_specification(self, user_description, custom_prompt=None):
        if not user_description:
            return False, None, "Please enter a description of your software requirements."
        
        try:
            # Generate the specification (model method now returns data or None)
            spec_data = self.generator.generate_specification(user_description, custom_prompt)

            if spec_data is None:
                # Error messages are now handled within the model/view via st.error
                return None # Indicate failure

            # Save to JSON file
            project_name = "unnamed_project"
            if isinstance(spec_data, dict) and "project_Overview" in spec_data and "project_Name" in spec_data["project_Overview"]:
                 project_name = spec_data["project_Overview"]["project_Name"] or project_name

            filename = get_filename(project_name=project_name, extension="spec.json") # Add suffix
            filepath = save_data_to_json_file(spec_data, filename)

            return spec_data

        except Exception as e:
            # Log error or display in Streamlit? View handles st.error now.
            print(f"Error in controller generate_specification: {str(e)}")
            return None # Indicate failure
    
    def load_specification(self, filepath):
        try:
            file_data = load_json_file(filepath)
        
            file_data = load_json_file(filepath)
            return file_data # Return data directly, message handled in view
        except Exception as e:
            print(f"Error loading specification: {str(e)}")
            return None # Indicate failure

    def generate_design_specification(self, spec_data):
        """Generates and saves the design specification based on the provided spec data."""
        if not spec_data or not isinstance(spec_data, dict):
            return None # Indicate failure

        try:
            # Generate the design specification using the model
            design_data = self.generator.generate_design(spec_data)

            if design_data is None:
                # Error messages handled within the model/view
                return None # Indicate failure

            # Save to JSON file
            project_name = "unnamed_project"
            if "project_Overview" in spec_data and "project_Name" in spec_data["project_Overview"]:
                 project_name = spec_data["project_Overview"]["project_Name"] or project_name

            filename = get_filename(project_name=project_name, extension="design.json") # Add suffix
            filepath = save_data_to_json_file(design_data, filename)

            # Return the generated data
            return design_data

        except Exception as e:
            print(f"Error in controller generate_design_specification: {str(e)}")
            return None # Indicate failure

    def export_to_markdown(self, spec_data):
        markdown_content = []
    
        # Project Overview
        if "project_Overview" in spec_data and isinstance(spec_data["project_Overview"], dict):
            overview = spec_data["project_Overview"]
            markdown_content.extend([
                f"# {overview.get('project_Name', 'Unnamed Project')}",
                "",
                "## Project Overview",
                f"**Purpose:** {overview.get('project_Purpose', 'N/A')}",
                f"**Scope:** {overview.get('product_Scope', 'N/A')}",
                ""
            ])

        # Functional Requirements
        if "functional_Requirements" in spec_data and isinstance(spec_data["functional_Requirements"], list):
            markdown_content.extend([
                "## Functional Requirements",
                ""
            ])
            for req in spec_data["functional_Requirements"]:
                markdown_content.extend([
                    f"### {req.get('id', 'FR-XXX')} - {req.get('title', 'N/A')}",
                    f"**Description:** {req.get('description', 'N/A')}",
                    f"**Priority:** {req.get('priority', 'N/A')}",
                    ""
                ])
                if "acceptance_criteria" in req and isinstance(req["acceptance_criteria"], list):
                    markdown_content.append("**Acceptance Criteria:**")
                    for criterion in req.get('acceptance_criteria', []):
                        markdown_content.append(f"- {criterion}")
                markdown_content.append("")
            
        # Non-Functional Requirements
        if "non_Functional_Requirements" in spec_data and isinstance(spec_data["non_Functional_Requirements"], list):
            markdown_content.extend([
                "## Non-Functional Requirements",
                ""
            ])
            for req in spec_data["non_Functional_Requirements"]:
                markdown_content.extend([
                    f"### {req.get('id', 'NFR-XXX')} - {req.get('category', 'N/A')}",
                    f"**Description:** {req.get('description')}",
                    ""
                ])
                if "acceptance_criteria" in req and isinstance(req["acceptance_criteria"], list):
                    markdown_content.append("**Acceptance Criteria:**")
                    for criterion in req.get('acceptance_criteria', []):
                        markdown_content.append(f"- {criterion}")
                markdown_content.append("")

        # External Interface Requirements
        if "external_Interface_Requirements" in spec_data and isinstance(spec_data["external_Interface_Requirements"], dict):
            interfaces = spec_data["external_Interface_Requirements"]
            markdown_content.extend([
                "## External Interface Requirements",
                ""
            ])
            ui_list = interfaces.get("user_Interfaces", [])
            if ui_list and isinstance(ui_list, list):
                markdown_content.append("### User Interfaces")
                for ui in ui_list: markdown_content.append(f"- {ui}")
                markdown_content.append("")
            
            hw_list = interfaces.get("hardware_Interfaces", [])
            if hw_list and isinstance(hw_list, list):
                markdown_content.append("### Hardware Interfaces")
                for hi in hw_list: markdown_content.append(f"- {hi}")
                markdown_content.append("")
            
            sw_list = interfaces.get("software_Interfaces", [])
            if sw_list and isinstance(sw_list, list):
                markdown_content.append("### Software Interfaces")
                for si in sw_list: markdown_content.append(f"- {si}")
                markdown_content.append("")
            
            comm_list = interfaces.get("communication_Interfaces", [])
            if comm_list and isinstance(comm_list, list):
                markdown_content.append("### Communication Interfaces")
                for ci in comm_list: markdown_content.append(f"- {ci}")
                markdown_content.append("")

        # Technology Stack
        if "technology_Stack" in spec_data and isinstance(spec_data["technology_Stack"], dict):
            tech_stack = spec_data["technology_Stack"]
            markdown_content.extend([
                "## Technology Stack",
                ""
            ])
            
            if "backend" in tech_stack and isinstance(tech_stack["backend"], dict):
                backend = tech_stack["backend"]
                markdown_content.extend([
                    "### Backend", "",
                    f"- **Language:** {backend.get('language', 'N/A')}",
                    f"- **Framework:** {backend.get('framework', 'N/A')}",
                    f"- **API Architecture:** {backend.get('api_Architecture', 'N/A')}", ""
                ])
            
            if "frontend" in tech_stack and isinstance(tech_stack["frontend"], dict):
                frontend = tech_stack["frontend"]
                markdown_content.extend([
                    "### Frontend", "",
                    f"- **Language:** {frontend.get('language', 'N/A')}",
                    f"- **Framework:** {frontend.get('framework', 'N/A')}",
                    f"- **Responsive Design:** {str(frontend.get('responsive_Design', 'N/A'))}", ""
                ])

        # Data Storage
        if "data_Storage" in spec_data and isinstance(spec_data["data_Storage"], dict):
            storage = spec_data["data_Storage"]
            markdown_content.extend([
                "## Data Storage", "",
                f"**Storage Type:** {storage.get('storage_Type', 'N/A')}",
                f"**Database Type:** {storage.get('database_Type', 'N/A')}", ""
            ])
            if "data_models" in storage and isinstance(storage["data_models"], list):
                markdown_content.append("### Data Models (Key Attributes)")
                for model in storage.get('data_models', []):
                    if isinstance(model, dict):
                        entity_name = model.get('entity_name', 'Unnamed Entity')
                        key_attrs = ", ".join(model.get('key_attributes', ['N/A']))
                        markdown_content.append(f"- **{entity_name}:** {key_attrs}")
                markdown_content.append("")

        # Assumptions Made
        if "assumptions_Made" in spec_data and isinstance(spec_data["assumptions_Made"], list):
            assumptions = spec_data.get("assumptions_Made", [])
            if assumptions:
                markdown_content.extend(["## Assumptions Made", ""])
                for assumption in assumptions:
                    markdown_content.append(f"- {assumption}")
                markdown_content.append("")

        # Metadata (if present)
        if "metadata" in spec_data and isinstance(spec_data["metadata"], dict):
            metadata = spec_data["metadata"]
            markdown_content.extend([
                "## Generation Metadata", "",
                f"- **Generated At:** {metadata.get('timestamp', 'N/A')}",
                # --- CHANGE HERE ---
                f"- **Model Used:** {metadata.get('model_used', 'N/A')}", # Changed from 'chosen_model'
                f"- **Generation Step:** {metadata.get('generation_step', 'N/A')}", # Added for clarity
                ""
            ])

        return "\n".join(markdown_content)
