import logging
import json
import os
from .base_agent import BaseAgent
from .prompt import DESIGN_PROMPT
from . import utils
from datetime import datetime

logger = logging.getLogger(__name__)

class DesignAgent(BaseAgent):
    def __init__(self):
        super().__init__(prompt_template=DESIGN_PROMPT, agent_type='spec_design')
        logger.info("DesignAgent initialized.")

    def generate_design(self, spec_data: dict) -> dict:
        if not isinstance(spec_data, dict) or not spec_data:
            logger.error("Input specification data must be a non-empty dictionary.")
            raise ValueError("Input specification data must be a non-empty dictionary.")

        try:
            logger.info("Generating system design from specification...")
            spec_json_string = json.dumps(spec_data, indent=2)
            response_text = self.chain.invoke({"agent1_output_json": spec_json_string})
            logger.info("Received response from model.")

            #parse the JSON response
            design_data = utils.parse_json_response(response_text)
            if not isinstance(design_data, dict):
                logger.error("Parsed design is not a valid dictionary.")
                raise ValueError("Model did not return a valid JSON dictionary structure.")

            # Add metadata for tracking.
            # Use the project name from the *source specification* for consistency.
            project_name = spec_data.get("project_Overview", {}).get("project_Name", "unnamed_project")
            design_data["metadata"] = {
                "generation_step": "design",
                "timestamp": datetime.now().isoformat(),
                "model_used": self.model_name, # model_name is an attribute from BaseAgent
                "source_specification_filepath": spec_data.get("metadata", {}).get("filepath")
            }

            # 1. Get the target directory.
            output_dir = utils.get_spec_design_output_dir()
            # 2. Generate a unique filename.
            filename = utils.generate_filename(project_name=project_name, extension="design.json")
            # 3. Combine into a full path.
            full_filepath = os.path.join(output_dir, filename)
            # 4. Save the file and store the path in metadata.
            design_data["metadata"]["filepath"] = full_filepath
            utils.save_json_to_file(design_data, full_filepath)
            
            logger.info(f"System design for '{project_name}' generated successfully.")

            return design_data

        except ValueError as ve:
            logger.error(f"A value error occurred during design generation: {ve}")
            raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred in generate_design: {e}")
            raise

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# class DesignAgent:
#     def __init__(self):
#         """Initialize the design agent with LangChain components."""
#         # Get API key for Google Gemini
#         self.api_key = get_api_key()
#         self.model_name = "gemini-2.0-flash"
        
#         # Initialize LangChain's Google Gemini model
#         self.llm = ChatGoogleGenerativeAI(
#             model="gemini-2.0-flash",
#             google_api_key=self.api_key,
#             temperature=0.3
#         )
        
#         # Define LangChain prompt template
#         self.prompt_template = ChatPromptTemplate.from_template(DESIGN_PROMPT)
        
#         # Create processing chain using the modern LCEL approach
#         self.chain = self.prompt_template | self.llm | StrOutputParser()

#     def generate_design(self, spec_data: dict) -> dict:
#         """Generate a system design from a specification JSON."""
#         if not isinstance(spec_data, dict):
#             logger.error("Invalid specification data: must be a dictionary.")
#             raise ValueError("Specification data must be a dictionary.")

#         try:
#             logger.info("Generating design specification...")
#             # Prepare input for prompt
#             spec_json_string = json.dumps(spec_data, indent=2)            
#             # Run LangChain LCEL chain
#             response_text = self.chain.invoke({"agent1_output_json": spec_json_string})
#             logger.info("Received response from model.")

#             # Parse JSON response
#             design_data = parse_json_response(response_text)
#             if not isinstance(design_data, dict):
#                 logger.error("Parsed design is not a dictionary.")
#                 raise ValueError("Model did not return valid JSON structure.")

#             # Add metadata
#             design_data["metadata"] = {
#                 "generation_step": "design",
#                 "timestamp": datetime.now().isoformat(),
#                 "model_used": self.model_name,
#                 "source_specification_timestamp": spec_data.get("metadata", {}).get("timestamp")
#             }

#             # Save to file
#             project_name = spec_data.get("project_Overview", {}).get("project_Name", "unnamed_project")
#             filename = get_filename(project_name=project_name, extension="design.json")
#             filepath = save_data_to_json_file(design_data, filename)
#             logger.info(f"Design saved to {filepath}")

#             return design_data

#         except Exception as e:
#             logger.exception(f"Error generating design: {str(e)}")
#             raise

#     def to_autogen_agent(self) -> ConversableAgent:
#         """Convert to an AutoGen ConversableAgent."""
#         return ConversableAgent(
#             name="DesignAgent",
#             system_message="I am a System Designer AI, creating detailed system designs from software specifications.",
#             llm_config=False,  # No LLM directly; use LangChain
#             human_input_mode="NEVER",
#             code_execution_config=False,
#             function_map={
#                 "generate_design": self.generate_design
#             }
#         )