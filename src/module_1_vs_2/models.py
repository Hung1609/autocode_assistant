import json
from datetime import datetime
import streamlit as st
import logging
from config import get_gemini_model
from prompts import SPECIFICATION_PROMPT, DESIGN_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpecificationGenerator:
    def __init__(self, model_name='gemini-2.0-flash'): 
        self.model = get_gemini_model(model_name)
        self.model_name = model_name

    def _parse_json_response(self, response_text):
        try:
            if "```json" in response_text:
                json_text = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
            elif response_text.strip().startswith('{') and response_text.strip().endswith('}'):
                 json_text = response_text.strip()
            else:
                 logger.warning("Response does not appear to be a markdown JSON block or a plain JSON object. Attempting direct parse, but this may fail or indicate LLM non-compliance.")
                 json_text = response_text
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parsing Error: {e}")
            logger.error(f"Raw Response Text causing error: ---START---\n{response_text}\n---END---")
            st.error(f"Error parsing JSON response from the model. The model might not have returned valid JSON. Raw response logged.")
            raise ValueError(f"Failed to parse JSON response: {e}. Raw text: {response_text[:500]}...")
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

            json_from_llm_result = self._parse_json_response(response.text)
            if not isinstance(json_from_llm_result, dict):
                logger.error("Parsed specification result is not a dictionary. Cannot proceed.")
                st.error("The model did not return the expected JSON structure for specification.")
                return None

            processed_result = json_from_llm_result.copy()
            project_name = "unnamed_project"
            if "project_Overview" in processed_result and isinstance(processed_result["project_Overview"], dict) and "project_Name" in processed_result["project_Overview"]:
                project_name = processed_result["project_Overview"]["project_Name"] or project_name
            elif "project_name" in processed_result: # Fallback
                project_name = processed_result["project_name"] or project_name
            
            # Ensure the project_Overview and project_Name keys exist in the processed_result for robustness
            if "project_Overview" not in processed_result or not isinstance(processed_result.get("project_Overview"), dict):
                processed_result["project_Overview"] = {}
            if "project_Name" not in processed_result["project_Overview"]:
                processed_result["project_Overview"]["project_Name"] = project_name


            # Add metadata
            processed_result["metadata"] = {
                "generation_step": "specification",
                "timestamp": datetime.now().isoformat(),
                "model_used": self.model_name,
                "original_description": user_description
            }
            logger.info(f"Specification generated and processed successfully for project: {project_name}")
            return processed_result

        except ValueError as e: 
            st.error(f"Specification Generation Error: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error during specification generation: {e}") 
            st.error(f"An unexpected error occurred during specification generation: {e}")
            return None

    def generate_design(self, specification_json_with_metadata):
        try:
            if not isinstance(specification_json_with_metadata, dict):
                 st.error("Invalid input: Specification data must be a dictionary.")
                 return None
            
            spec_keys_for_prompt = [
                "project_Overview", "functional_Requirements", "non_Functional_Requirements",
                "external_Interface_Requirements", "technology_Stack", "data_Storage", "assumptions_Made"
            ]
            clean_specification_json = {
                key: specification_json_with_metadata[key]
                for key in spec_keys_for_prompt if key in specification_json_with_metadata
            }

            # Convert the input specification dict to a JSON string for the prompt
            spec_json_string_for_prompt = json.dumps(specification_json_with_metadata, indent=2)

            # Format the DESIGN_PROMPT
            full_prompt = DESIGN_PROMPT.format(agent1_output_json=spec_json_string_for_prompt)

            logger.info("Generating design specification...")
            response = self.model.generate_content(full_prompt)
            logger.info("Received design response from model.")

            json_from_llm_result = self._parse_json_response(response.text)

            if not isinstance(json_from_llm_result, dict):
                logger.error("Parsed design result is not a dictionary. Cannot proceed.")
                st.error("The model did not return the expected JSON structure for design.")
                return None

            processed_result = json_from_llm_result.copy()

            processed_result["metadata"] = {
                "generation_step": "design",
                "timestamp": datetime.now().isoformat(),
                "model_used": self.model_name,
                "source_specification_timestamp": specification_json_with_metadata.get("metadata", {}).get("timestamp")
            }
            
            project_name = specification_json_with_metadata.get("project_Overview", {}).get("project_Name", "unnamed_project")
            logger.info(f"Design generated and processed successfully for project: {project_name}")
            return processed_result

        except ValueError as e:
             st.error(f"Design Generation Error: {e}")
             return None
        except Exception as e:
            logger.exception(f"Unexpected error during design generation: {e}")
            st.error(f"An unexpected error occurred during design generation: {e}")
            return None
