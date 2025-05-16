import streamlit as st
import json
from controllers import SpecificationController
import re

def slugify(text):
    text = text.lower()
    text = re.sub(r'\s+', '_', text)
    text = re.sub(r'[^\w_]', '', text)
    return text

class SpecificationView:
    def __init__(self):
        self.controller = SpecificationController()
        if "spec_data" not in st.session_state:
            st.session_state.spec_data = None
        if "design_data" not in st.session_state:
            st.session_state.design_data = None
        if "user_description" not in st.session_state:
            st.session_state.user_description = ""
        if "spec_markdown" not in st.session_state:
            st.session_state.spec_markdown = ""

    def display_ui(self):
        st.set_page_config(page_title="Specification & Design Generator", layout="wide")
        st.title("Software Specification & Design Generator")
        st.markdown("Generate technical specifications and system designs from natural language descriptions.")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("1. Enter Software Requirements")
            st.session_state.user_description = st.text_area(
                "Describe your software requirements:",
                value=st.session_state.user_description,
                height=150,
                key="user_input_area",
                placeholder="E.g., Create a task management app where users can create projects, add tasks with deadlines, and invite team members to collaborate"
            )

            if st.button("Generate Specification", use_container_width=True, key="gen_spec_btn"):
                if not st.session_state.user_description.strip():
                    st.warning("Please enter a description first.")
                else:
                    with st.spinner("Generating specification... Please wait."):
                        st.session_state.design_data = None
                        st.session_state.spec_markdown = ""

                        spec_data_result = self.controller.generate_specification(st.session_state.user_description)
                        if spec_data_result:
                            st.session_state.spec_data = spec_data_result
                            st.session_state.spec_markdown = self.controller.export_to_markdown(spec_data_result)
                            st.success("Specification generated successfully!")
                        else:
                            st.session_state.spec_data = None
            
            if st.session_state.spec_data:
                if st.button("Generate Design from Specification", use_container_width=True, key="gen_design_btn"):
                    with st.spinner("Generating design... This may take a moment."):
                        design_data_result = self.controller.generate_design_specification(st.session_state.spec_data)
                        if design_data_result:
                            st.session_state.design_data = design_data_result
                            st.success("Design generated successfully!")
                        else:
                            st.session_state.design_data = None


        with col2:
            if st.session_state.spec_data:
                st.subheader("2. Generated Specification")
                # Add download button for specification JSON
                spec_json_str = json.dumps(st.session_state.spec_data, indent=2)
                st.download_button(
                    label="Download Specification (JSON)",
                    data=spec_json_str,
                    file_name=f"{st.session_state.spec_data.get('project_Overview',{}).get('project_Name','unnamed_project').replace(' ','_')}.spec.json",
                    mime="application/json",
                    key="download_spec_json"
                )
                # Add download button for specification Markdown
                if st.session_state.spec_markdown:
                    st.download_button(
                        label="Download Specification (Markdown)",
                        data=st.session_state.spec_markdown,
                        file_name=f"{st.session_state.spec_data.get('project_Overview',{}).get('project_Name','unnamed_project').replace(' ','_')}.spec.md",
                        mime="text/markdown",
                        key="download_spec_md"
                    )
                self.display_specification_data(st.session_state.spec_data)

            if st.session_state.design_data:
                st.subheader("3. Generated Design")
                 # Add download button for design JSON
                design_json_str = json.dumps(st.session_state.design_data, indent=2)
                project_name_for_file = "unnamed_project"
                if st.session_state.spec_data and "project_Overview" in st.session_state.spec_data and "project_Name" in st.session_state.spec_data["project_Overview"]:
                    project_name_for_file = st.session_state.spec_data["project_Overview"]["project_Name"]

                st.download_button(
                    label="Download Design (JSON)",
                    data=design_json_str,
                    file_name=f"{project_name_for_file.replace(' ','_')}.design.json",
                    mime="application/json",
                    key="download_design_json"
                )
                self.display_design_data(st.session_state.design_data)


    def display_specification_data(self, spec_data):
        if not spec_data or not isinstance(spec_data, dict):
            st.warning("No specification data available to display.")
            return

        overview = spec_data.get("project_Overview", {})
        st.markdown(f"#### Project: {overview.get('project_Name', 'Unnamed Project')}")
        with st.expander("Project Overview", expanded=False):
            st.markdown(f"**Purpose:** {overview.get('project_Purpose', 'N/A')}")
            st.markdown(f"**Scope:** {overview.get('product_Scope', 'N/A')}")

        spec_tabs = st.tabs([
            "Functional Req.", "Non-Functional Req.", "Interfaces",
            "Tech Stack", "Data Storage", "Assumptions", "Raw JSON"
        ])

        with spec_tabs[0]: # Functional Requirements
            reqs = spec_data.get("functional_Requirements", [])
            if reqs:
                for i, req in enumerate(reqs):
                    if not isinstance(req, dict): continue
                    with st.expander(f"{req.get('id', f'FR-{i+1:03d}')} - {req.get('title', 'Requirement')}", expanded=False):
                        st.markdown(f"**Description:** {req.get('description', 'N/A')}")
                        st.markdown(f"**Priority:** {req.get('priority', 'N/A')}")
                        criteria = req.get('acceptance_criteria', [])
                        if criteria and isinstance(criteria, list):
                            st.markdown("**Acceptance Criteria:**")
                            for criterion in criteria: st.markdown(f"- {criterion}")
            else: st.info("No functional requirements found.")

        with spec_tabs[1]: # Non-Functional Requirements
            reqs = spec_data.get("non_Functional_Requirements", [])
            if reqs:
                for i, req in enumerate(reqs):
                    if not isinstance(req, dict): continue
                    with st.expander(f"{req.get('id', f'NFR-{i+1:03d}')} - {req.get('category', 'Category')}", expanded=False):
                        st.markdown(f"**Description:** {req.get('description', 'N/A')}")
                        criteria = req.get('acceptance_criteria', [])
                        if criteria and isinstance(criteria, list):
                            st.markdown("**Acceptance Criteria:**")
                            for criterion in criteria: st.markdown(f"- {criterion}")
            else: st.info("No non-functional requirements found.")

        with spec_tabs[2]: # External Interfaces
            interfaces = spec_data.get("external_Interface_Requirements", {})
            if interfaces and isinstance(interfaces, dict):
                for key, title in [("user_Interfaces", "User Interfaces"), 
                                   ("hardware_Interfaces", "Hardware Interfaces"),
                                   ("software_Interfaces", "Software Interfaces"),
                                   ("communication_Interfaces", "Communication Interfaces")]:
                    items = interfaces.get(key, [])
                    if items and isinstance(items, list):
                        st.markdown(f"**{title}:**")
                        for item in items: st.markdown(f"- {item}")
                    else: st.markdown(f"**{title}:** N/A")
            else: st.info("No external interface requirements found.")

        with spec_tabs[3]: # Technology Stack
            tech_stack = spec_data.get("technology_Stack", {})
            if tech_stack and isinstance(tech_stack, dict):
                backend = tech_stack.get("backend", {})
                if isinstance(backend, dict):
                    st.markdown("**Backend:**")
                    st.markdown(f"- Language: {backend.get('language', 'N/A')}")
                    st.markdown(f"- Framework: {backend.get('framework', 'N/A')}")
                    st.markdown(f"- API Arch: {backend.get('api_Architecture', 'N/A')}")
                frontend = tech_stack.get("frontend", {})
                if isinstance(frontend, dict):
                    st.markdown("**Frontend:**")
                    st.markdown(f"- Language: {frontend.get('language', 'N/A')}")
                    st.markdown(f"- Framework: {frontend.get('framework', 'N/A')}")
                    st.markdown(f"- Responsive: {frontend.get('responsive_Design', 'N/A')}")
            else: st.info("No technology stack found.")

        with spec_tabs[4]: # Data Storage
            storage = spec_data.get("data_Storage", {})
            if storage and isinstance(storage, dict):
                st.markdown(f"**Storage Type:** {storage.get('storage_Type', 'N/A')}")
                st.markdown(f"**Database Type:** {storage.get('database_Type', 'N/A')}")
                models = storage.get("data_models", [])
                if models and isinstance(models, list):
                    st.markdown("**Data Models (Key Attributes):**")
                    for model in models:
                         if isinstance(model, dict): # Expected format from SPECIFICATION_PROMPT
                             st.markdown(f"- **{model.get('entity_name', 'Unknown Entity')}:** {', '.join(model.get('key_attributes', ['N/A']))}")
                         # Removed the 'else' for old string format to strictly follow new prompt.
                else: st.markdown("**Data Models:** N/A")
            else: st.info("No data storage information found.")

        with spec_tabs[5]: # Assumptions
             assumptions = spec_data.get("assumptions_Made", [])
             if assumptions and isinstance(assumptions, list):
                 st.markdown("\n".join([f"- {a}" for a in assumptions]))
             else: st.info("No assumptions listed.")

        with spec_tabs[6]: # Raw JSON
            st.json(spec_data)


    def display_design_data(self, design_data):
        if not design_data or not isinstance(design_data, dict):
            st.warning("No design data available to display.")
            return

        design_tabs = st.tabs([
            "Architecture", "Data Design", "Interfaces (API)",
            "Workflows", "Folder Structure", "Dependencies", "Raw JSON"
        ])

        with design_tabs[0]: # System Architecture
            arch = design_data.get("system_Architecture", {})
            if arch and isinstance(arch, dict):
                st.markdown(f"**Description:** {arch.get('description', 'N/A')}")
                components = arch.get("components", [])
                if components and isinstance(components, list):
                    st.markdown("**Components:**")
                    for comp in components:
                        if not isinstance(comp, dict): continue
                        with st.expander(f"{comp.get('name', 'Component')}", expanded=False):
                            st.markdown(f"**Description:** {comp.get('description', 'N/A')}")
                            st.markdown(f"**Technologies:** {', '.join(comp.get('technologies', ['N/A']))}")
                            st.markdown(f"**Inputs:** {', '.join(comp.get('inputs', ['N/A']))}")
                            st.markdown(f"**Outputs:** {', '.join(comp.get('outputs', ['N/A']))}")
                else: st.markdown("**Components:** N/A")
            else: st.info("No architecture information found.")

        with design_tabs[1]: # Data Design
            data = design_data.get("data_Design", {})
            if data and isinstance(data, dict):
                st.markdown(f"**Data Flow:** {data.get('data_Flow_Description', 'N/A')}")
                st.markdown(f"**Storage Type:** {data.get('storage_Type', 'N/A')}")
                st.markdown(f"**Database Type:** {data.get('database_Type', 'N/A')}")
                
                models = data.get("data_Models", [])
                if models and isinstance(models, list):
                    st.markdown("**Data Models:**")
                    for model in models:
                        if not isinstance(model, dict): continue
                        with st.expander(f"{model.get('model_Name', 'Model')}", expanded=False):
                             st.markdown(f"**Description:** {model.get('description', 'N/A')}")
                             # --- REMOVED storage_Location ---
                             # st.markdown(f"**Storage:** {model.get('storage_Location', 'N/A')}") # Not in DESIGN_PROMPT

                             fields = model.get("fields", [])
                             if fields and isinstance(fields, list):
                                 st.markdown("**Fields:**")
                                 for field in fields:
                                     if not isinstance(field, dict): continue
                                     constraints_list = field.get('constraints', [])
                                     constraints_str = f" [{', '.join(constraints_list)}]" if constraints_list else ""
                                     st.markdown(f"- **{field.get('name', 'field')}** ({field.get('type', 'N/A')}): {field.get('description', 'N/A')}{constraints_str}")
                             
                             relationships = model.get("relationships", [])
                             if relationships and isinstance(relationships, list):
                                 st.markdown("**Relationships:**")
                                 for rel in relationships:
                                     if not isinstance(rel, dict): continue
                                     # --- UPDATED relationship display ---
                                     st.markdown(f"- **Field:** `{rel.get('field_Name', '?')}`")
                                     st.markdown(f"  - **Type:** {rel.get('type', '?')}") # Changed from relationship_Type
                                     st.markdown(f"  - **Related Model:** `{rel.get('related_Model', '?')}` (links via `{rel.get('foreign_Field', '?')}`)")
                                     st.markdown(f"  - **Description:** {rel.get('description', 'N/A')}")
                                     st.markdown(f"  - **Implementation Notes:** {rel.get('implementation_Notes', 'N/A')}")
                                     if rel.get('on_Delete'): # Optional field
                                         st.markdown(f"  - **On Delete:** {rel.get('on_Delete')}")
                else: st.markdown("**Data Models:** N/A")
            else: st.info("No data design information found.")

        with design_tabs[2]: # Interface Design (API)
            interface = design_data.get("interface_Design", {})
            if interface and isinstance(interface, dict):
                st.markdown(f"**UI Interaction Notes:** {interface.get('ui_Interaction_Notes', 'N/A')}")
                apis = interface.get("api_Specifications", [])
                if apis and isinstance(apis, list):
                    st.markdown("**API Specifications:**")
                    for api in apis:
                         if not isinstance(api, dict): continue
                         auth_tag = '[Auth Required]' if api.get('authentication_Required') else '[No Auth]'
                         with st.expander(f"{api.get('method', '?')} {api.get('endpoint', '/?')} {auth_tag}", expanded=False):
                             st.markdown(f"**Description:** {api.get('description', 'N/A')}")
                             req = api.get('request_Format', {})
                             res = api.get('response_Format', {})
                             
                             req_params = ', '.join(req.get('params',[])) or 'None'
                             req_query = ', '.join(req.get('query',[])) or 'None'
                             req_body_desc = req.get('body_Schema', {}).get('description', 'N/A') if isinstance(req.get('body_Schema'), dict) else 'N/A'
                             
                             st.markdown(f"**Request:** Params: `{req_params}`, Query: `{req_query}`, Body: `{req_body_desc}`")
                             
                             success_status = res.get('success_Status', '?')
                             success_schema_desc = res.get('success_Schema', {}).get('description', 'N/A') if isinstance(res.get('success_Schema'), dict) else 'N/A'
                             error_status_list = res.get('error_Status', [])
                             error_status_str = ', '.join(map(str, error_status_list)) if error_status_list else '?'
                             error_schema_desc = res.get('error_Schema', {}).get('description', 'N/A') if isinstance(res.get('error_Schema'), dict) else 'N/A'

                             st.markdown(f"**Response:** Success (`{success_status}`): `{success_schema_desc}`, Error (`{error_status_str}`): `{error_schema_desc}`")
                             st.markdown(f"**Related NFRs:** {', '.join(api.get('related_NFRs', ['N/A']))}")
                else: st.markdown("**API Specifications:** N/A")
            else: st.info("No interface design information found.")

        with design_tabs[3]: # Workflows
            workflows = design_data.get("workflow_Interaction", [])
            if workflows and isinstance(workflows, list):
                for wf in workflows:
                    if not isinstance(wf, dict): continue
                    with st.expander(f"{wf.get('workflow_Name', 'Workflow')}", expanded=False):
                        st.markdown(f"**Description:**")
                        # For step-by-step descriptions, preserve newlines
                        desc_steps = wf.get('description', 'N/A').splitlines()
                        for step in desc_steps:
                            st.markdown(step) # Renders each line as a new paragraph
                        st.markdown(f"**Related Requirements:** {', '.join(wf.get('related_Requirements', ['N/A']))}")
            else: st.info("No workflow information found.")

        with design_tabs[4]: # Folder Structure
            folder = design_data.get("folder_Structure", {})
            if folder and isinstance(folder, dict):
                st.markdown(f"**Description:** {folder.get('description', 'N/A')}")
                root_dir_name = folder.get('root_Project_Directory_Name', 'project_root')
                st.markdown(f"**Root Project Directory Name:** `{root_dir_name}`")
                structure_items = folder.get("structure", [])
                if structure_items and isinstance(structure_items, list):
                    st.markdown("**Structure (relative to `{root_dir_name}/`):**")
                    for item in structure_items:
                        if not isinstance(item, dict): continue
                        path_display = item.get('path', '?') 
                        description = item.get('description', 'N/A')
                        is_directory = 'directory' in description.lower()
                        if is_directory:
                            st.markdown(f"- `{path_display}/` (Directory): {description}")
                        else:
                            st.markdown(f"- `{path_display}` (File): {description}")
                else: st.markdown("**Structure:** N/A")
            else: st.info("No folder structure information found.")

        with design_tabs[5]: # Dependencies
            deps = design_data.get("dependencies", {})
            if deps and isinstance(deps, dict):
                backend_deps = deps.get('backend', [])
                if backend_deps and isinstance(backend_deps, list):
                    st.markdown("**Backend:**")
                    st.code(f"{', '.join(backend_deps)}", language=None) # Using st.code for better display
                else: st.markdown("**Backend:** N/A")
                
                frontend_deps = deps.get('frontend', [])
                if frontend_deps and isinstance(frontend_deps, list) and frontend_deps: # Check if list is not empty
                    st.markdown("**Frontend:**")
                    st.code(f"{', '.join(frontend_deps)}", language=None)
                else: st.markdown("**Frontend:** N/A or Vanilla (no explicit dependencies)")
            else: st.info("No dependency information found.")

        with design_tabs[6]: # Raw JSON
            st.json(design_data)
