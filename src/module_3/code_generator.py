import os
import json
import logging
from pathlib import Path
import re

# Use relative imports assuming standard package structure
from .config import get_gemini_model
from .prompts import select_prompt_for_file

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CodeGenerator:
    def __init__(self, design_filepath, output_base_dir="generated_code", model_name="gemini-1.5-flash"):
        """
        Initializes the CodeGenerator.

        Args:
            design_filepath (str): Path to the design specification JSON file.
            output_base_dir (str): The base directory where generated code will be saved.
            model_name (str): Name of the Gemini model to use.
        """
        self.design_filepath = Path(design_filepath)
        self.output_base_dir = Path(output_base_dir)
        self.design_data = self._load_design()
        try:
            # Initialize the actual Gemini model via config
            self.model = get_gemini_model(model_name)
        except Exception as e:
            logger.error(f"Failed to initialize LLM model: {e}")
            # Decide how to handle this - maybe raise the error or set model to None
            self.model = None
            raise # Re-raise the exception to prevent proceeding without a model

    def _load_design(self):
        try:
            with open(self.design_filepath, 'r', encoding='utf-8') as f:
                design = json.load(f)
            logger.info(f"Successfully loaded design file: {self.design_filepath}")
            # Basic validation of design structure
            if "folder_Structure" not in design or "structure" not in design["folder_Structure"]:
                 logger.warning("Design file is missing 'folder_Structure' or 'structure' key.")
                 design["folder_Structure"] = {"structure": []} # Ensure it exists
            if "technology_Stack" not in design:
                 logger.warning("Design file is missing 'technology_Stack'.")
                 design["technology_Stack"] = {} # Ensure it exists
            return design
        except FileNotFoundError:
            logger.error(f"Design file not found: {self.design_filepath}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from file: {self.design_filepath}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading the design file: {e}")
            raise

    def generate_codebase(self):
        if not self.model:
             logger.error("LLM Model not initialized. Cannot generate codebase.")
             return
        if not self.design_data:
            logger.error("Design data not loaded. Cannot generate codebase.")
            return

        folder_structure = self.design_data.get("folder_Structure", {}).get("structure", [])
        if not folder_structure:
            logger.warning("No folder structure defined in the design specification. Nothing to generate.")
            return

        logger.info(f"Starting codebase generation in: {self.output_base_dir}")
        self.output_base_dir.mkdir(parents=True, exist_ok=True) # Create base output directory

        for item in folder_structure:
            item_path_str = item.get("path")
            item_description = item.get("description", "")

            if not item_path_str:
                logger.warning(f"Skipping item with no path: {item}")
                continue

            # Treat paths starting with / as relative to the output base dir
            relative_path_str = item_path_str.lstrip('/')
            full_path = self.output_base_dir / relative_path_str

            # Determine if it's likely a file or directory
            # Heuristic: Check for extension or if description explicitly mentions 'directory' or 'folder'
            has_extension = '.' in Path(relative_path_str).name
            is_likely_dir = 'directory' in item_description.lower() or 'folder' in item_description.lower()

            if has_extension and not is_likely_dir:
                # Create parent directories if they don't exist
                full_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"Generating file: {full_path} ({item_description})")
                self._generate_file(full_path, item)
            else:
                # Assume it's a directory if no extension or description indicates it
                full_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {full_path}")

        logger.info("Codebase generation process completed.")

    def _get_relevant_context(self, file_info):
        """
        Extracts context relevant to generating a specific file from the design JSON.
        Tailors context based on file type/path.
        """
        context = {
            "target_file_path": file_info.get("path"),
            "target_file_description": file_info.get("description"),
            "technology_stack": self.design_data.get("technology_Stack", {}),
            # Add more specific context based on file type below
        }
        file_path = context["target_file_path"].lower()
        tech_stack = context["technology_stack"]

        # Context for Backend Models/Schemas
        if ("model" in file_path or "schema" in file_path) and "backend" in file_path:
            context["data_design"] = self.design_data.get("data_Design", {})
            logger.debug(f"Added data_design context for {file_path}")

        # Context for Backend Controllers/Routes
        elif ("controller" in file_path or "route" in file_path or "view" in file_path) and "backend" in file_path:
            context["api_specifications"] = self.design_data.get("interface_Design", {}).get("api_Specifications", [])
            context["related_workflows"] = self.design_data.get("workflow_Interaction", []) # Might be useful
            context["data_models_summary"] = [m.get("model_Name") for m in self.design_data.get("data_Design", {}).get("data_Models", [])] # Just names might be enough
            logger.debug(f"Added api_specifications context for {file_path}")

        # Context for Frontend Components
        elif tech_stack.get("frontend") and tech_stack["frontend"].get("framework") in ["React", "Vue", "Angular"] and ("component" in file_path or ".js" in file_path or ".jsx" in file_path or ".vue" in file_path):
             context["ui_interaction_notes"] = self.design_data.get("interface_Design", {}).get("ui_Interaction_Notes", "")
             # Maybe related API endpoints it might call?
             context["api_endpoints_summary"] = [f"{api.get('method')} {api.get('endpoint')}" for api in self.design_data.get("interface_Design", {}).get("api_Specifications", [])]
             logger.debug(f"Added frontend component context for {file_path}")

        # Add more specific context extraction logic here for other file types (HTML, CSS, configs etc.)

        # Optionally include a summary of the overall project overview
        context["project_overview"] = self.design_data.get("project_Overview", {})

        return context

    def _clean_llm_output(self, raw_code):
        """ Basic cleaning of LLM code output (e.g., remove markdown backticks). """
        # Remove ```python, ```javascript, ``` etc.
        cleaned_code = re.sub(r'^```[a-zA-Z]*\n', '', raw_code)
        cleaned_code = re.sub(r'\n```$', '', cleaned_code)
        return cleaned_code.strip()

    def _generate_file(self, file_path: Path, file_info: dict):
        """
        Generates content for a single file using the LLM.
        """
        if not self.model:
             logger.error(f"LLM Model not available. Skipping generation for {file_path}")
             return

        tech_stack = self.design_data.get("technology_Stack", {})
        context_data = self._get_relevant_context(file_info)
        # Use the imported prompt selection function
        prompt_template = select_prompt_for_file(file_info, tech_stack)

        # Format the prompt with the extracted context
        try:
            # Convert context dict to a JSON string for reliable insertion
            context_str = json.dumps(context_data, indent=2)
            full_prompt = prompt_template.format(
                context=context_str,
                file_path=context_data["target_file_path"] # Pass file path separately if needed by prompt
            )
        except KeyError as e:
             logger.error(f"Placeholder {{{e}}} not found in prompt template for {file_path}. Prompt starts with: '{prompt_template[:150]}...'")
             return # Skip file generation if prompt formatting fails
        except Exception as e:
            logger.error(f"Error formatting prompt for {file_path}: {e}")
            return

        try:
            logger.info(f"Calling LLM for {file_path}...")
            # === Actual LLM Call ===
            # Ensure the model is available before calling
            if self.model:
                 response = self.model.generate_content(full_prompt)
                 generated_code = self._clean_llm_output(response.text)
            else:
                 logger.error("LLM model is not initialized. Cannot generate code.")
                 generated_code = f"# Error: LLM Model not initialized for {file_path}\n"
            # === End Actual LLM Call ===

            if not generated_code:
                 logger.warning(f"LLM returned empty or invalid code for {file_path}. Skipping write.")
                 return

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(generated_code)
            logger.info(f"Successfully wrote code to {file_path}")

        except Exception as e:
            # Log the full prompt that caused the error for debugging
            logger.error(f"Failed to generate or write file {file_path}: {e}\n--- Prompt Start ---\n{full_prompt[:1000]}...\n--- Prompt End ---")


# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Example Usage: Point to a design file in outputs and generate code
    design_file_path = Path("outputs/to_do_web_app_20250421.design.json") # Adjust to your actual design file
    output_directory = "generated_project_code" # Define where the code should go

    if not design_file_path.exists():
        logger.error(f"Design file '{design_file_path}' not found. Please generate a design file first or update the path.")
    else:
        logger.info(f"--- Starting Code Generation from: {design_file_path} ---")
        try:
            # Initialize the generator with the actual design file
            code_gen = CodeGenerator(design_filepath=str(design_file_path), output_base_dir=output_directory)
            # Run the generation process
            code_gen.generate_codebase()
            logger.info(f"--- Code Generation Finished. Check folder: '{output_directory}' ---")
        except ValueError as e:
             logger.error(f"Initialization failed: {e}") # Catch errors like missing API key
        except Exception as e:
             logger.error(f"An unexpected error occurred during code generation: {e}", exc_info=True) # Log traceback
