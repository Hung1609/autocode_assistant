import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from autogen import ConversableAgent
from .prompt import DESIGN_PROMPT
from .setup import get_api_key
from .utils import parse_json_response, save_data_to_json_file, get_filename
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DesignAgent:
    def __init__(self):
        """Initialize the design agent with LangChain components."""
        # Get API key for Google Gemini
        self.api_key = get_api_key()
        self.model_name = "gemini-2.0-flash"
        
        # Initialize LangChain's Google Gemini model
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=self.api_key,
            temperature=0.3
        )
        
        # Define LangChain prompt template
        self.prompt_template = ChatPromptTemplate.from_template(DESIGN_PROMPT)
        
        # Create processing chain using the modern LCEL approach
        self.chain = self.prompt_template | self.llm | StrOutputParser()

    def generate_design(self, spec_data: dict) -> dict:
        """Generate a system design from a specification JSON."""
        if not isinstance(spec_data, dict):
            logger.error("Invalid specification data: must be a dictionary.")
            raise ValueError("Specification data must be a dictionary.")

        try:
            logger.info("Generating design specification...")
            # Prepare input for prompt
            spec_json_string = json.dumps(spec_data, indent=2)            
            # Run LangChain LCEL chain
            response_text = self.chain.invoke({"agent1_output_json": spec_json_string})
            logger.info("Received response from model.")

            # Parse JSON response
            design_data = parse_json_response(response_text)
            if not isinstance(design_data, dict):
                logger.error("Parsed design is not a dictionary.")
                raise ValueError("Model did not return valid JSON structure.")

            # Add metadata
            design_data["metadata"] = {
                "generation_step": "design",
                "timestamp": datetime.now().isoformat(),
                "model_used": self.model_name,
                "source_specification_timestamp": spec_data.get("metadata", {}).get("timestamp")
            }

            # Save to file
            project_name = spec_data.get("project_Overview", {}).get("project_Name", "unnamed_project")
            filename = get_filename(project_name=project_name, extension="design.json")
            filepath = save_data_to_json_file(design_data, filename)
            logger.info(f"Design saved to {filepath}")

            return design_data

        except Exception as e:
            logger.exception(f"Error generating design: {str(e)}")
            raise

    def to_autogen_agent(self) -> ConversableAgent:
        """Convert to an AutoGen ConversableAgent."""
        return ConversableAgent(
            name="DesignAgent",
            system_message="I am a System Designer AI, creating detailed system designs from software specifications.",
            llm_config=False,  # No LLM directly; use LangChain
            human_input_mode="NEVER",
            code_execution_config=False,
            function_map={
                "generate_design": self.generate_design
            }
        )