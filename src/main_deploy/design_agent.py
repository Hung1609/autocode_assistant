import json
import logging
from datetime import datetime
import google.generativeai as genai
from prompt import DESIGN_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DesignAgent:
    def __init__(self, model_name='gemini-2.0-flash', api_key=None):
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be provided.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name

    def _parse_json_response(self, response_text):
        if "```json" in response_text:
            json_text = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif response_text.strip().startswith('{') and response_text.strip().endswith('}'):
            json_text = response_text.strip()
        else:
            logger.warning("Response does not appear to be a markdown JSON block or plain JSON. Attempting direct parse.")
            json_text = response_text
        return json.loads(json_text)

    def generate_design(self, specification_json):
        if not isinstance(specification_json, dict):
            logger.error("Invalid input: Specification data must be a dictionary.")
            return None

        # Prepare specification JSON for prompt
        spec_keys = [
            "project_Overview", "functional_Requirements", "non_Functional_Requirements",
            "external_Interface_Requirements", "technology_Stack", "data_Storage", "assumptions_Made"
        ]
        clean_spec = {key: specification_json[key] for key in spec_keys if key in specification_json}
        spec_json_string = json.dumps(clean_spec, indent=2)

        # Format the DESIGN_PROMPT
        prompt = DESIGN_PROMPT.format(agent1_output_json=spec_json_string)
        logger.info("Generating design specification...")
        response = self.model.generate_content(prompt)
        logger.info("Received design response from model.")

        json_result = self._parse_json_response(response.text)
        if not isinstance(json_result, dict):
            logger.error("Parsed design result is not a dictionary.")
            return None

        processed_result = json_result.copy()
        processed_result["metadata"] = {
            "generation_step": "design",
            "timestamp": datetime.now().isoformat(),
            "model_used": self.model_name,
            "source_specification_timestamp": specification_json.get("metadata", {}).get("timestamp")
        }

        project_name = specification_json.get("project_Overview", {}).get("project_Name", "unnamed_project")
        logger.info(f"Design generated successfully for project: {project_name}")
        return processed_result