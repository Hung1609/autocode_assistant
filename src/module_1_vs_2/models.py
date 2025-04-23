import json
from datetime import datetime
import streamlit as st
import logging

from config import get_gemini_model
from prompts import SPECIFICATION_PROMPT, DESIGN_PROMPT

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpecificationGenerator:
    # Use a more capable model if needed for complex JSON generation
    def __init__(self, model_name='gemini-2.5-pro-exp-03-25'): 
        self.model = get_gemini_model(model_name)
        self.model_name = model_name

    def _parse_json_response(self, response_text):
        try:
            if "```json" in response_text:
                json_text = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
            elif response_text.strip().startswith('{') and response_text.strip().endswith('}'):
                 # Handle cases where the response is just the JSON object
                 json_text = response_text.strip()
            else:
                 # Assume it might be plain text JSON, try parsing directly
                 # This might fail if there's introductory text.
                 logger.warning("Response does not appear to be well-formatted JSON or markdown JSON block. Attempting direct parse.")
                 json_text = response_text

            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parsing Error: {e}")
            logger.error(f"Raw Response Text: {response_text}")
            st.error(f"Error parsing JSON response from the model. Raw response logged.")
            raise ValueError(f"Failed to parse JSON response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during JSON parsing: {e}")
            logger.error(f"Raw Response Text: {response_text}")
            st.error(f"An unexpected error occurred while parsing the response.")
            raise

    def generate_specification(self, user_description, prompt_template=None):
        try:
            if prompt_template is None:
                prompt_template = SPECIFICATION_PROMPT
                
            full_prompt = prompt_template.format(user_description=user_description)
            logger.info("Generating specification...")
            response = self.model.generate_content(full_prompt)
            logger.info("Received response from model.")

            result = self._parse_json_response(response.text)

            # Ensure project_name exists in the parsed result
            project_name = "unnamed_project"
            if isinstance(result, dict):
                 if "project_Overview" in result and "project_Name" in result["project_Overview"]:
                     project_name = result["project_Overview"]["project_Name"] or project_name
                 # Fallback if project_Overview is missing
                 elif "project_name" in result:
                     project_name = result["project_name"] or project_name
                 # Ensure the key exists even if unnamed
                 if "project_Overview" not in result:
                     result["project_Overview"] = {}
                 if "project_Name" not in result["project_Overview"]:
                     result["project_Overview"]["project_Name"] = project_name


            # Add metadata
            if isinstance(result, dict): # Add metadata only if parsing succeeded and got a dict
                result["metadata"] = {
                    "generation_step": "specification",
                    "timestamp": datetime.now().isoformat(),
                    "model_used": self.model_name,
                    "original_description": user_description
                }
            else:
                 logger.error("Parsed result is not a dictionary. Cannot add metadata.")
                 return None

            logger.info(f"Specification generated successfully for project: {project_name}")
            return result

        except ValueError as e: 
             st.error(f"Specification Generation Error: {e}")
             return None
        except Exception as e:
            logger.exception(f"Unexpected error during specification generation: {e}") 
            st.error(f"An unexpected error occurred during specification generation: {e}")
            return None

    def generate_design(self, specification_json):
        try:
            if not isinstance(specification_json, dict):
                 st.error("Invalid input: Specification data must be a dictionary.")
                 return None

            # Convert the input specification dict to a JSON string for the prompt
            spec_json_string = json.dumps(specification_json, indent=2)

            # Format the DESIGN_PROMPT
            full_prompt = DESIGN_PROMPT.format(agent1_output_json=spec_json_string)

            logger.info("Generating design specification...")
            response = self.model.generate_content(full_prompt)
            logger.info("Received design response from model.")

            # Parse JSON response using helper
            result = self._parse_json_response(response.text)

            # Add metadata
            if isinstance(result, dict):
                result["metadata"] = {
                    "generation_step": "design",
                    "timestamp": datetime.now().isoformat(),
                    "model_used": self.model_name,
                    # Optionally link back to the source spec, e.g., by timestamp or a unique ID if available
                    "source_specification_timestamp": specification_json.get("metadata", {}).get("timestamp")
                }
                project_name = specification_json.get("project_Overview", {}).get("project_Name", "unnamed_project")
                logger.info(f"Design generated successfully for project: {project_name}")
            else:
                 logger.error("Parsed design result is not a dictionary. Cannot add metadata.")
                 return None

            return result

        except ValueError as e:
             st.error(f"Design Generation Error: {e}")
             return None
        except Exception as e:
            logger.exception(f"Unexpected error during design generation: {e}")
            st.error(f"An unexpected error occurred during design generation: {e}")
            return None
