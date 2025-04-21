import streamlit as st
import json
from controllers import SpecificationController
# Removed unused imports: datetime, get_output_files, load_json_file

class SpecificationView:
    def __init__(self):
        self.controller = SpecificationController()
        # Initialize session state keys if they don't exist
        if "spec_data" not in st.session_state:
            st.session_state.spec_data = None
        if "design_data" not in st.session_state:
            st.session_state.design_data = None
        if "user_description" not in st.session_state:
            st.session_state.user_description = ""

    def display_ui(self):
        st.set_page_config(page_title="Specification & Design Generator", layout="wide")
        st.title("Software Specification & Design Generator")
        st.markdown("Generate technical specifications and system designs from natural language descriptions using Gemini.")

        # --- Input Area ---
        st.subheader("1. Enter Software Requirements")
        st.session_state.user_description = st.text_area(
            "Describe your software requirements",
            value=st.session_state.user_description, # Persist input
            height=150,
            placeholder="E.g., Create a task management app where users can create projects, add tasks with deadlines, and invite team members to collaborate"
        )

        # --- Generate Specification Button ---
        if st.button("Generate Specification", use_container_width=True, key="gen_spec_btn"):
            if not st.session_state.user_description:
                st.warning("Please enter a description first.")
            else:
                with st.spinner("Generating specification... Please wait."):
                    # Clear previous design data when generating a new spec
                    st.session_state.design_data = None
                    # Generate specification
                    spec_data = self.controller.generate_specification(st.session_state.user_description)
                    if spec_data:
                        st.session_state.spec_data = spec_data
                        st.success("Specification generated successfully!")
                        # Automatically trigger display update
                        st.rerun()
                    else:
                        # Error message is handled by the model/controller via st.error
                        st.error("Failed to generate specification. Check logs if errors persist.")
                        st.session_state.spec_data = None # Clear potentially partial data

        st.markdown("---") # Separator

        # --- Display Specification Area ---
        if st.session_state.spec_data:
            st.subheader("2. Generated Specification")
            self.display_specification_data(st.session_state.spec_data)

            # --- Generate Design Button (appears only after spec is generated) ---
            if st.button("Generate Design from Specification", use_container_width=True, key="gen_design_btn"):
                with st.spinner("Generating design... This may take a moment."):
                    design_data = self.controller.generate_design_specification(st.session_state.spec_data)
                    if design_data:
                        st.session_state.design_data = design_data
                        st.success("Design generated successfully!")
                        # Automatically trigger display update
                        st.rerun()
                    else:
                        st.error("Failed to generate design. Check logs if errors persist.")
                        st.session_state.design_data = None # Clear potentially partial data

            st.markdown("---") # Separator

        # --- Display Design Area ---
        if st.session_state.design_data:
            st.subheader("3. Generated Design")
            self.display_design_data(st.session_state.design_data)


    def display_specification_data(self, spec_data):
        if not spec_data or not isinstance(spec_data, dict):
            st.warning("No specification data available to display.")
            return

        # Display project name and overview
        overview = spec_data.get("project_Overview", {})
        st.markdown(f"#### {overview.get('project_Name', 'Unnamed Project')}")
        with st.expander("Project Overview", expanded=False):
            st.markdown(f"**Purpose:** {overview.get('project_Purpose', 'N/A')}")
            st.markdown(f"**Scope:** {overview.get('product_Scope', 'N/A')}")

        # Create tabs for different sections
        spec_tabs = st.tabs([
            "Functional Req.",
            "Non-Functional Req.",
            "Interfaces",
            "Tech Stack",
            "Data Storage",
            "Assumptions",
            "Raw JSON"
        ])

        # Functional Requirements
        with spec_tabs[0]:
            reqs = spec_data.get("functional_Requirements", [])
            if reqs:
                for req in reqs:
                    with st.expander(f"{req.get('id', 'FR')} - {req.get('title', 'Requirement')}"):
                        st.markdown(f"**Description:** {req.get('description', 'N/A')}")
                        st.markdown(f"**Priority:** {req.get('priority', 'N/A')}")
                        criteria = req.get('acceptance_criteria', [])
                        if criteria:
                            st.markdown("**Acceptance Criteria:**")
                            for criterion in criteria:
                                st.markdown(f"- {criterion}")
            else:
                st.info("No functional requirements found.")

        # Non-Functional Requirements
        with spec_tabs[1]:
            reqs = spec_data.get("non_Functional_Requirements", [])
            if reqs:
                for req in reqs:
                    with st.expander(f"{req.get('id', 'NFR')} - {req.get('category', 'Requirement')}"):
                        st.markdown(f"**Description:** {req.get('description', 'N/A')}")
                        criteria = req.get('acceptance_criteria', [])
                        if criteria:
                            st.markdown("**Acceptance Criteria:**")
                            for criterion in criteria:
                                st.markdown(f"- {criterion}")
            else:
                st.info("No non-functional requirements found.")

        # External Interfaces
        with spec_tabs[2]:
            interfaces = spec_data.get("external_Interface_Requirements", {})
            if interfaces:
                st.markdown("**User Interfaces:**")
                st.markdown("\n".join([f"- {ui}" for ui in interfaces.get("user_Interfaces", ["N/A"])]))
                st.markdown("**Hardware Interfaces:**")
                st.markdown("\n".join([f"- {hi}" for hi in interfaces.get("hardware_Interfaces", ["N/A"])]))
                st.markdown("**Software Interfaces:**")
                st.markdown("\n".join([f"- {si}" for si in interfaces.get("software_Interfaces", ["N/A"])]))
                st.markdown("**Communication Interfaces:**")
                st.markdown("\n".join([f"- {ci}" for ci in interfaces.get("communication_Interfaces", ["N/A"])]))
            else:
                st.info("No external interface requirements found.")

        # Technology Stack
        with spec_tabs[3]:
            tech_stack = spec_data.get("technology_Stack", {})
            if tech_stack:
                backend = tech_stack.get("backend", {})
                frontend = tech_stack.get("frontend", {})
                st.markdown("**Backend:**")
                st.markdown(f"- Language: {backend.get('language', 'N/A')}")
                st.markdown(f"- Framework: {backend.get('framework', 'N/A')}")
                st.markdown(f"- API Arch: {backend.get('api_Architecture', 'N/A')}")
                st.markdown("**Frontend:**")
                st.markdown(f"- Language: {frontend.get('language', 'N/A')}")
                st.markdown(f"- Framework: {frontend.get('framework', 'N/A')}")
                st.markdown(f"- Responsive: {frontend.get('responsive_Design', 'N/A')}")
            else:
                st.info("No technology stack found.")

        # Data Storage
        with spec_tabs[4]:
            storage = spec_data.get("data_Storage", {})
            if storage:
                st.markdown(f"**Storage Type:** {storage.get('storage_Type', 'N/A')}")
                st.markdown(f"**Database Type:** {storage.get('database_Type', 'N/A')}")
                models = storage.get("data_models", [])
                if models:
                    st.markdown("**Data Models (Key Attributes):**")
                    for model in models:
                         if isinstance(model, dict):
                             st.markdown(f"- **{model.get('entity_name', 'Unknown Entity')}:** {', '.join(model.get('key_attributes', []))}")
                         else: # Handle old string format if necessary
                             st.markdown(f"- {model}")

            else:
                st.info("No data storage information found.")

        # Assumptions
        with spec_tabs[5]:
             assumptions = spec_data.get("assumptions_Made", [])
             if assumptions:
                 st.markdown("\n".join([f"- {a}" for a in assumptions]))
             else:
                 st.info("No assumptions listed.")

        # Raw JSON
        with spec_tabs[6]:
            st.json(spec_data)

    def display_design_data(self, design_data):
        if not design_data or not isinstance(design_data, dict):
            st.warning("No design data available to display.")
            return

        # Create tabs for different sections
        design_tabs = st.tabs([
            "Architecture",
            "Data Design",
            "Interfaces (API)",
            "Workflows",
            "Folder Structure",
            "Dependencies",
            "Raw JSON"
        ])

        # System Architecture
        with design_tabs[0]:
            arch = design_data.get("system_Architecture", {})
            if arch:
                st.markdown(f"**Description:** {arch.get('description', 'N/A')}")
                st.markdown("**Components:**")
                for comp in arch.get("components", []):
                    with st.expander(f"{comp.get('name', 'Component')}"):
                        st.markdown(f"**Description:** {comp.get('description', 'N/A')}")
                        st.markdown(f"**Technologies:** {', '.join(comp.get('technologies', ['N/A']))}")
                        st.markdown(f"**Inputs:** {', '.join(comp.get('inputs', ['N/A']))}")
                        st.markdown(f"**Outputs:** {', '.join(comp.get('outputs', ['N/A']))}")
            else:
                st.info("No architecture information found.")

        # Data Design
        with design_tabs[1]:
            data = design_data.get("data_Design", {})
            if data:
                st.markdown(f"**Data Flow:** {data.get('data_Flow_Description', 'N/A')}")
                st.markdown(f"**Storage Type:** {data.get('storage_Type', 'N/A')}")
                st.markdown(f"**Database Type:** {data.get('database_Type', 'N/A')}")
                st.markdown("**Data Models:**")
                for model in data.get("data_Models", []):
                    with st.expander(f"{model.get('model_Name', 'Model')}"):
                         st.markdown(f"**Description:** {model.get('description', 'N/A')}")
                         st.markdown(f"**Storage:** {model.get('storage_Location', 'N/A')}")
                         st.markdown("**Fields:**")
                         for field in model.get("fields", []):
                             constraints = ', '.join(field.get('constraints', []))
                             st.markdown(f"- **{field.get('name', 'field')}** ({field.get('type', 'N/A')}): {field.get('description', 'N/A')} {f'[{constraints}]' if constraints else ''}")
                         st.markdown("**Relationships:**")
                         for rel in model.get("relationships", []):
                             st.markdown(f"- Field `{rel.get('field_Name', '?')}` relates to `{rel.get('related_Model', '?')}` ({rel.get('relationship_Type', '?')}). Notes: {rel.get('implementation_Notes', 'N/A')}")

            else:
                st.info("No data design information found.")

        # Interface Design (API)
        with design_tabs[2]:
            interface = design_data.get("interface_Design", {})
            if interface:
                st.markdown(f"**UI Interaction Notes:** {interface.get('ui_Interaction_Notes', 'N/A')}")
                st.markdown("**API Specifications:**")
                for api in interface.get("api_Specifications", []):
                     with st.expander(f"{api.get('method', '?')} {api.get('endpoint', '/?')} {'[Auth]' if api.get('authentication_Required') else ''}"):
                         st.markdown(f"**Description:** {api.get('description', 'N/A')}")
                         req = api.get('request_Format', {})
                         res = api.get('response_Format', {})
                         st.markdown(f"**Request:** Params: `{', '.join(req.get('params',[])) or 'None'}`, Query: `{', '.join(req.get('query',[])) or 'None'}`, Body: `{req.get('body_Schema', {}).get('description', 'N/A')}`")
                         st.markdown(f"**Response:** Success (`{res.get('success_Status', '?')}`): `{res.get('success_Schema', {}).get('description', 'N/A')}`, Error (`{', '.join(map(str, res.get('error_Status',[]))) or '?'}`): `{res.get('error_Schema', {}).get('description', 'N/A')}`")
                         st.markdown(f"**Related NFRs:** {', '.join(api.get('related_NFRs', ['N/A']))}")
            else:
                st.info("No interface design information found.")

        # Workflows
        with design_tabs[3]:
            workflows = design_data.get("workflow_Interaction", [])
            if workflows:
                for wf in workflows:
                    with st.expander(f"{wf.get('workflow_Name', 'Workflow')}"):
                        st.markdown(f"**Description:** {wf.get('description', 'N/A')}")
                        st.markdown(f"**Related Requirements:** {', '.join(wf.get('related_Requirements', ['N/A']))}")
            else:
                st.info("No workflow information found.")

        # Folder Structure
        with design_tabs[4]:
            folder = design_data.get("folder_Structure", {})
            if folder:
                st.markdown(f"**Description:** {folder.get('description', 'N/A')}")
                st.markdown("**Structure:**")
                for item in folder.get("structure", []):
                    st.markdown(f"- `{item.get('path', '?')}`: {item.get('description', 'N/A')}")
            else:
                st.info("No folder structure information found.")

        # Dependencies
        with design_tabs[5]:
            deps = design_data.get("dependencies", {})
            if deps:
                st.markdown("**Backend:**")
                st.markdown(f"`{', '.join(deps.get('backend', ['N/A']))}`")
                st.markdown("**Frontend:**")
                st.markdown(f"`{', '.join(deps.get('frontend', ['N/A']))}`")
            else:
                st.info("No dependency information found.")

        # Raw JSON
        with design_tabs[6]:
            st.json(design_data)
