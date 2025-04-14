import streamlit as st
import json
import os
import time
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Cấu hình Gemini API Key
def configure_genai():
    api_key = st.session_state.get("api_key", "")
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

# Function to create a timestamped filename
def get_timestamp_filename(prefix="spec", extension="json"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"

# Lưu JSON file
def save_to_json(data, filename=None):
    if filename is None:
        filename = get_timestamp_filename()
    
    # Create 'outputs' directory if it doesn't exist
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
    
    filepath = os.path.join("outputs", filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath

# Function to generate technical specification using Gemini
def generate_spec(user_description, prompt_template):
    if not configure_genai():
        st.error("Please enter your Gemini API Key")
        return None

    try:
        # Set up the model
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Prepare the prompt by filling in the template
        full_prompt = prompt_template.format(user_description=user_description)
        
        # Generate content
        response = model.generate_content(full_prompt)
        
        # Parse the JSON content from the response
        try:
            # First try to directly parse as JSON
            response_text = response.text
            if "```json" in response_text:
                # Extract JSON if it's in a code block
                json_text = response_text.split("```json")[1].split("```")[0].strip()
                result = json.loads(json_text)
            else:
                # Try to parse the whole response as JSON
                result = json.loads(response_text)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract just the JSON portion
            try:
                # Look for JSON-like structure and clean it up
                response_text = response.text
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_text = response_text[start_idx:end_idx]
                    result = json.loads(json_text)
                else:
                    # Return raw text if JSON parsing fails
                    result = {"raw_response": response.text}
            except:
                result = {"raw_response": response.text}
        
        # Add metadata
        result["metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "model": "gemini-2.0-flash",
            "original_description": user_description
        }
        
        return result
    
    except Exception as e:
        st.error(f"Error generating specification: {str(e)}")
        return None

# Default prompt template
default_prompt_template = """
# Objective
You are an AI Agent that act as a project manager, your task is to convert natural language software requirements into a structured technical specification in JSON format.

# Context
The user will provide a description of software requirements in natural language. Your task is to analyze these requirements and convert them into a structured technical specification that can be used by developers to implement the software.

# Instructions
1. Carefully analyze the provided description: "{user_description}"
2. Identify all functional requirements, non-functional requirements, user stories, and constraints.
3. Structure the information into a complete and detailed technical specification.
4. Ensure all requirements are clear, specific, measurable, and achievable.
5. If there are ambiguities, make reasonable assumptions and note them.

# Output Requirements
Return a JSON object with the following structure:
```json
{{
  "project_name": "Name of the project",
  "overview": "Brief summary of the project",
  "functional_requirements": [
    {{
      "id": "FR-001",
      "title": "Requirement title",
      "description": "Detailed description",
      "priority": "High/Medium/Low",
      "acceptance_criteria": ["Criterion 1", "Criterion 2"]
    }}
    // Additional functional requirements...
  ],
  "non_functional_requirements": [
    {{
      "id": "NFR-001",
      "category": "Performance/Security/Usability/etc.",
      "description": "Detailed description",
      "constraints": "Specific constraints"
    }}
    // Additional non-functional requirements...
  ],
  "data_entities": [
    {{
      "name": "Entity name",
      "attributes": [
        {{
          "name": "attribute_name",
          "type": "data type",
          "description": "Description"
        }}
      ],
      "relationships": ["Relationship with other entities"]
    }}
    // Additional entities...
  ],
  "api_endpoints": [
    {{
      "path": "/endpoint-path",
      "method": "GET/POST/PUT/DELETE",
      "description": "What this endpoint does",
      "request_parameters": [
        {{
          "name": "parameter_name",
          "type": "data type",
          "required": true/false,
          "description": "Description"
        }}
      ],
      "response": {{
        "success": "Example of success response",
        "error": "Example of error response"
      }}
    }}
    // Additional endpoints...
  ],
  "assumptions": [
    "Assumption 1",
    "Assumption 2"
  ],
  "open_questions": [
    "Question 1",
    "Question 2"
  ]
}}
```

# Example
For input: "Create a task management app where users can create projects, add tasks with deadlines, and invite team members to collaborate"

Output would include:
- Project name and overview
- Functional requirements such as user registration, project creation, task management, user invitation, etc.
- Non-functional requirements like performance, security, and usability
- Data entities for Users, Projects, Tasks, etc.
- API endpoints for user operations, project operations, task operations, etc.
- Any assumptions made or questions that need clarification
"""

# Streamlit UI
def main():
    st.set_page_config(page_title="Module 1 - Software Requirements Specification Generator", layout="wide")
    
    st.title("Module 1 - Software Requirements Specification Generator")
    st.markdown("This tool converts natural language descriptions into structured technical specifications.")
    
    # API Key input in sidebar
    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input("Enter your Gemini API Key", type="password")
        st.session_state["api_key"] = api_key
        
        st.markdown("---")
        st.subheader("About")
        st.markdown("""
        This tool uses Google's Gemini AI to convert natural language descriptions 
        into structured technical specifications in JSON format.
        """)
    
    # Main content area with two tabs
    tab1, tab2 = st.tabs(["Generate Specification", "Advanced Settings"])
    
    with tab1:
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
                st.session_state.prompt_template = default_prompt_template
            
            # Generate button
            if st.button("Generate Specification", use_container_width=True):
                if not user_description:
                    st.warning("Please enter a description of your software requirements.")
                else:
                    with st.spinner("Generating technical specification..."):
                        spec_data = generate_spec(user_description, st.session_state.prompt_template)
                        
                        if spec_data:
                            # Save to JSON file
                            filename = get_timestamp_filename()
                            filepath = save_to_json(spec_data, filename)
                            
                            # Store in session state
                            st.session_state.spec_data = spec_data
                            st.session_state.filepath = filepath
                            
                            st.success(f"Specification generated and saved to {filepath}")
        
        with col2:
            st.subheader("Generated Files")
            
            # Display list of generated files
            if os.path.exists("outputs"):
                files = [f for f in os.listdir("outputs") if f.endswith('.json')]
                if files:
                    files.sort(key=lambda x: os.path.getmtime(os.path.join("outputs", x)), reverse=True)
                    
                    selected_file = st.selectbox("Select a file to view", files)
                    
                    if st.button("Load Selected File", use_container_width=True):
                        file_path = os.path.join("outputs", selected_file)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_data = json.load(f)
                        
                        st.session_state.spec_data = file_data
                        st.session_state.filepath = file_path
                        st.success(f"Loaded specification from {file_path}")
                else:
                    st.info("No generated files yet.")
            else:
                st.info("No generated files yet.")
    
    with tab2:
        st.subheader("Customize Prompt Template")
        custom_prompt = st.text_area(
            "Edit the prompt template used for generation",
            value=st.session_state.get("prompt_template", default_prompt_template),
            height=400
        )
        
        if st.button("Save Template", use_container_width=True):
            st.session_state.prompt_template = custom_prompt
            st.success("Prompt template updated")
    
    # Display the generated specification
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
            
            # Non-Functional Requirements
            with spec_tabs[1]:
                if "non_functional_requirements" in spec_data and spec_data["non_functional_requirements"]:
                    for req in spec_data["non_functional_requirements"]:
                        with st.expander(f"{req.get('id', 'NFR')} - {req.get('category', 'Requirement')}"):
                            st.markdown(f"**Description:** {req.get('description', 'N/A')}")
                            if "constraints" in req:
                                st.markdown(f"**Constraints:** {req.get('constraints', 'N/A')}")
                else:
                    st.info("No non-functional requirements specified.")
            
            # Data Entities
            with spec_tabs[2]:
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
            
            # API Endpoints
            with spec_tabs[3]:
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
            
            # Assumptions & Questions
            with spec_tabs[4]:
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
            
            # Raw JSON
            with spec_tabs[5]:
                st.json(spec_data)
        
        # Download button
        if "filepath" in st.session_state:
            with open(st.session_state.filepath, "rb") as file:
                st.download_button(
                    label="Download JSON File",
                    data=file,
                    file_name=os.path.basename(st.session_state.filepath),
                    mime="application/json"
                )

if __name__ == "__main__":
    main()