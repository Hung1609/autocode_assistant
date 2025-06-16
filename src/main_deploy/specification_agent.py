import logging
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.chains import LLMChain
from autogen import ConversableAgent
from .prompt import SPECIFICATION_PROMPT
from .setup import get_gemini_model
from .utils import parse_json_response, save_data_to_json_file, get_filename
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpecificationAgent:
    def __init__(self):
        """Initialize the specification agent with LangChain components."""
        self.model = get_gemini_model(model_name="gemini-2.0-flash")
        self.model_name = "gemini-2.0-flash"
        # Define LangChain prompt template
        self.prompt_template = ChatPromptTemplate.from_template(SPECIFICATION_PROMPT)
        # Create LangChain chain
        self.chain = LLMChain(
            llm=self.model,
            prompt=self.prompt_template,
            output_parser=StrOutputParser()
        )

    def generate_specification(self, user_description: str) -> dict:
        """Generate a software specification from user description."""
        if not user_description.strip():
            logger.error("Empty user description provided.")
            raise ValueError("User description cannot be empty.")

        try:
            logger.info("Generating specification...")
            # Run LangChain chain
            response_text = self.chain.run(user_description=user_description)
            logger.info("Received response from model.")

            # Parse JSON response
            spec_data = parse_json_response(response_text)
            if not isinstance(spec_data, dict):
                logger.error("Parsed specification is not a dictionary.")
                raise ValueError("Model did not return valid JSON structure.")

            # Process and add metadata
            project_name = spec_data.get("project_Overview", {}).get("project_Name", "unnamed_project")
            spec_data["metadata"] = {
                "generation_step": "specification",
                "timestamp": datetime.now().isoformat(),
                "model_used": self.model_name,
                "original_description": user_description
            }

            # Save to file
            filename = get_filename(project_name=project_name, extension="spec.json")
            filepath = save_data_to_json_file(spec_data, filename)
            logger.info(f"Specification saved to {filepath}")

            return spec_data

        except Exception as e:
            logger.exception(f"Error generating specification: {str(e)}")
            raise

    def to_autogen_agent(self) -> ConversableAgent:
        """Convert to an AutoGen ConversableAgent."""
        return ConversableAgent(
            name="SpecificationAgent",
            system_message="I am a Requirements Analyst AI, generating structured software specifications from user descriptions.",
            llm_config=False,  # No LLM directly; use LangChain
            human_input_mode="NEVER",
            code_execution_config=False,
            function_map={
                "generate_specification": self.generate_specification
            }
        )