import os
from specification_agent import SpecificationAgent
from design_agent import DesignAgent
from utils import save_data_to_json_file
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        return

    spec_agent = SpecificationAgent(api_key=api_key)
    design_agent = DesignAgent(api_key=api_key)

    print("\nEnter your software project requirements (type 'DONE' on a new line to finish):")
    user_input = []
    while True:
        line = input()
        if line.strip().upper() == "DONE":
            break
        user_input.append(line)
    
    user_description = "\n".join(user_input).strip()
    if not user_description:
        logger.error("No input provided.")
        print("Error: No input provided.")
        return

    print("\nGenerating specification...")
    spec_data = spec_agent.generate_specification(user_description)
    if not spec_data:
        print("Failed to generate specification. Check logs for details.")
        return

    spec_filename = save_data_to_json_file(spec_data, extension="spec.json")
    print(f"Specification saved to: {spec_filename}")

    print("\nGenerating design specification...")
    design_data = design_agent.generate_design(spec_data)
    if not design_data:
        print("Failed to generate design specification. Check logs for details.")
        return

    design_filename = save_data_to_json_file(design_data, extension="design.json")
    print(f"Design specification saved to: {design_filename}")

if __name__ == "__main__":
    main()