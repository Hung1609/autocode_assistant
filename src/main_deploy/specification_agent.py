import json
import logging
from datetime import datetime
import google.generativeai as genai
from prompt import SPECIFICATION_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpecificationAgent:
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

    def generate_specification(self, user_description, prompt_template=None):
        if not user_description:
            logger.error("No user description provided.")
            return None

        prompt = (prompt_template or SPECIFICATION_PROMPT).format(user_description=user_description)
        logger.info("Generating specification...")
        response = self.model.generate_content(prompt)
        logger.info("Received response from model.")

        json_result = self._parse_json_response(response.text)
        if not isinstance(json_result, dict):
            logger.error("Parsed specification result is not a dictionary.")
            return None

        processed_result = json_result.copy()
        project_name = processed_result.get("project_Overview", {}).get("project_Name", "unnamed_project")

        if "project_Overview" not in processed_result:
            processed_result["project_Overview"] = {}
        if "project_Name" not in processed_result["project_Overview"]:
            processed_result["project_Overview"]["project_Name"] = project_name

        processed_result["metadata"] = {
            "generation_step": "specification",
            "timestamp": datetime.now().isoformat(),
            "model_used": self.model_name,
            "original_description": user_description
        }

        logger.info(f"Specification generated successfully for project: {project_name}")
        return processed_result