"""
This module contains UI components and presentation logic for the application.
"""

import streamlit as st
import json
from datetime import datetime

from controllers import SpecificationController
from utils import get_output_files, load_json_file

class SpecificationView:
    """
    View class for displaying the specification generator UI.
    """
    
    def __init__(self):
        """Initialize the specification view."""
        self.controller = SpecificationController()
    
    def display_ui(self):
        """
        Display the main UI for the specification generator.
        """
        st.set_page_config(page_title="Module 1 - Software Requirements Specification Generator", layout="wide")
        st.title("Module 1 - Software Requirements Specification Generator")
        st.markdown("This tool converts natural language descriptions into structured technical specifications.")
        
        # Sidebar
        with st.sidebar:
            st.header("Configuration")
            st.markdown("---")
            st.markdown("This module is using Gemini API to process.")
        
        # Main content area with two tabs
        tab1, tab2 = st.tabs(["Generate Specification", "Advanced Settings"])
        
        with tab1:
            self.display_generation_tab()
        
        with tab2:
            self.display_settings_tab()
        
        # Display the generated specification
        self.display_specification()
    
    def display_generation_tab(self):
        """
        Display the tab for generating specifications.
        """
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Enter Software Requirements")
            user_description = st.text_area(
                "Describe your software requirements",
                height=200,
                placeholder="E.g., Create a task management app where users can create projects, add tasks with deadlines, and invite team members to collaborate"
            )
            
            # Store the prompt template in session state
            if "prompt_template" not in st.session_state:
                st.session_state.prompt_template = None
            
            # Generate button
            if st.button("Generate Specification", use_container_width=True):
                # Generate specification using the controller
                success, result, message = self.controller.generate_specification(user_description, st.session_state.get("prompt_template"))
                
                if success:
                    st.session_state.spec_data = result
                    st.success(message)
                else:
                    st.error(message)
        
        with col2:
            st.subheader("Generated Files")
            self.display_generated_files()
    
    def display_generated_files(self):
        """
        Display a list of generated files and allow the user to load them.
        """
        files = get_output_files()
        
        if files:
            selected_file = st.selectbox("Select a file to view", files)
            
            if st.button("Load Selected File", use_container_width=True):
                # Load specification using the controller
                file_path = f"outputs/{selected_file}"
                success, file_data, message = self.controller.load_specification(file_path)
                
                if success:
                    st.session_state.spec_data = file_data
                    st.success(message)
                else:
                    st.error(message)
        else:
            st.info("No generated files yet.")
    
    def display_settings_tab(self):
        """
        Display the tab for customizing settings.
        """
        st.subheader("Customize Prompt Template")
        custom_prompt = st.text_area(
            "Edit the prompt template used for generation",
            value=st.session_state.get("prompt_template", ""),
            height=400
        )
        
        if st.button("Save Template", use_container_width=True):
            st.session_state.prompt_template = custom_prompt
            st.success("Prompt template updated")
    
    def display_specification(self):
        """
        Display the generated specification.
        """
        if "spec_data" in st.session_state:
            st.markdown("---")
            st.subheader("Generated Specification")
            
            spec_data = st.session_state.spec_data
            
            # Display project name and overview
            if "project_name" in spec_data:
                st.markdown(f"## {spec_data['project_name']}")
            
            if "overview" in spec_data:
                st.markdown(f"**Overview:** {spec_data['overview']}")
            
            # Create tabs for different sections
            if any(key in spec_data for key in ["functional_requirements", "non_functional_requirements", 
                                             "data_entities", "api_endpoints", "assumptions", "open_questions"]):
                
                spec_tabs = st.tabs([
                    "Functional Requirements", 
                    "Non-Functional Requirements",
                    "Data Entities",
                    "API Endpoints",
                    "Assumptions & Questions",
                    "Raw JSON"
                ])
                
                # Functional Requirements
                with spec_tabs[0]:
                    self.display_functional_requirements(spec_data)
                
                # Non-Functional Requirements
                with spec_tabs[1]:
                    self.display_non_functional_requirements(spec_data)
                
                # Data Entities
                with spec_tabs[2]:
                    self.display_data_entities(spec_data)
                
                # API Endpoints
                with spec_tabs[3]:
                    self.display_api_endpoints(spec_data)
                
                # Assumptions & Questions
                with spec_tabs[4]:
                    self.display_assumptions_questions(spec_data)
                
                # Raw JSON
                with spec_tabs[5]:
                    st.json(spec_data)
            
            # Download buttons
            self.display_download_buttons(spec_data)
    
    def display_functional_requirements(self, spec_data):
        """
        Display functional requirements in a tab.
        """
        if "functional_requirements" in spec_data and spec_data["functional_requirements"]:
            for req in spec_data["functional_requirements"]:
                with st.expander(f"{req.get('id', 'FR')} - {req.get('title', 'Requirement')}"):
                    st.markdown(f"**Description:** {req.get('description', 'N/A')}")
                    st.markdown(f"**Priority:** {req.get('priority', 'N/A')}")
                    
                    if "acceptance_criteria" in req and req["acceptance_criteria"]:
                        st.markdown("**Acceptance Criteria:**")
                        for ac in req["acceptance_criteria"]:
                            st.markdown(f"- {ac}")
        else:
            st.info("No functional requirements specified.")
    
    def display_non_functional_requirements(self, spec_data):
        """
        Display non-functional requirements in a tab.
        """
        if "non_functional_requirements" in spec_data and spec_data["non_functional_requirements"]:
            for req in spec_data["non_functional_requirements"]:
                with st.expander(f"{req.get('id', 'NFR')} - {req.get('category', 'Requirement')}"):
                    st.markdown(f"**Description:** {req.get('description', 'N/A')}")
                    if "constraints" in req:
                        st.markdown(f"**Constraints:** {req.get('constraints', 'N/A')}")
        else:
            st.info("No non-functional requirements specified.")
    
    def display_data_entities(self, spec_data):
        """
        Display data entities in a tab.
        """
        if "data_entities" in spec_data and spec_data["data_entities"]:
            for entity in spec_data["data_entities"]:
                with st.expander(f"Entity: {entity.get('name', 'Entity')}"):
                    if "attributes" in entity and entity["attributes"]:
                        st.markdown("**Attributes:**")
                        for attr in entity["attributes"]:
                            st.markdown(f"- **{attr.get('name', 'Attribute')}** ({attr.get('type', 'N/A')}): {attr.get('description', 'N/A')}")
                    
                    if "relationships" in entity and entity["relationships"]:
                        st.markdown("**Relationships:**")
                        for rel in entity["relationships"]:
                            st.markdown(f"- {rel}")
        else:
            st.info("No data entities specified.")
    
    def display_api_endpoints(self, spec_data):
        """
        Display API endpoints in a tab.
        """
        if "api_endpoints" in spec_data and spec_data["api_endpoints"]:
            for endpoint in spec_data["api_endpoints"]:
                with st.expander(f"{endpoint.get('method', 'GET')} {endpoint.get('path', '/endpoint')}"):
                    st.markdown(f"**Description:** {endpoint.get('description', 'N/A')}")
                    
                    if "request_parameters" in endpoint and endpoint["request_parameters"]:
                        st.markdown("**Request Parameters:**")
                        for param in endpoint["request_parameters"]:
                            required = "Required" if param.get("required", False) else "Optional"
                            st.markdown(f"- **{param.get('name', 'param')}** ({param.get('type', 'N/A')}, {required}): {param.get('description', 'N/A')}")
                    
                    if "response" in endpoint:
                        st.markdown("**Response:**")
                        if "success" in endpoint["response"]:
                            st.markdown(f"- **Success:** {endpoint['response']['success']}")
                        if "error" in endpoint["response"]:
                            st.markdown(f"- **Error:** {endpoint['response']['error']}")
        else:
            st.info("No API endpoints specified.")
    
    def display_assumptions_questions(self, spec_data):
        """
        Display assumptions and questions in a tab.
        """
        if "assumptions" in spec_data and spec_data["assumptions"]:
            st.markdown("### Assumptions")
            for assumption in spec_data["assumptions"]:
                st.markdown(f"- {assumption}")
        else:
            st.info("No assumptions specified.")
        
        st.markdown("---")
        
        if "open_questions" in spec_data and spec_data["open_questions"]:
            st.markdown("### Open Questions")
            for question in spec_data["open_questions"]:
                st.markdown(f"- {question}")
        else:
            st.info("No open questions specified.")
        
        # Display resolved questions if available
        if "resolved_questions" in spec_data and spec_data["resolved_questions"]:
            st.markdown("### Automatically Resolved Questions")
            for item in spec_data["resolved_questions"]:
                confidence_color = {
                    "High": "green",
                    "Medium": "orange",
                    "Low": "red"
                }.get(item.get("confidence", "Medium"), "orange")
                
                st.markdown(f"- **Q:** {item['question']}")
                st.markdown(f"  **A:** {item['answer']} <span style='color:{confidence_color}'>(Confidence: {item.get('confidence', 'Medium')})</span>", unsafe_allow_html=True)
    
    def display_download_buttons(self, spec_data):
        """
        Display download buttons for JSON and Markdown formats.
        """
        col1, col2 = st.columns(2)
        
        with col1: #JSON
            json_str = json.dumps(spec_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name=f"specification_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col2: #Markdown
            markdown_content = self.controller.export_to_markdown(spec_data)
            st.download_button(
                label="Download as Markdown",
                data=markdown_content,
                file_name=f"{spec_data.get('project_name', 'unnamed_project')}_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
                use_container_width=True
            )
