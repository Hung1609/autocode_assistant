#!/usr/bin/env python3
"""
Autonomous Code Generation System - Main Entry Point
---------------------------------------------------
This script orchestrates the entire process:
1. Taking user requirements
2. Analyzing and generating specifications in JSON
3. Generating code based on the JSON specification
4. Creating tests and fixing bugs automatically
"""

import os
import argparse
import logging
import subprocess
from typing import Optional


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoCodeSystem:
    """Main class for the autonomous code generation system."""
    
    def __init__(self, 
                 requirements_file: Optional[str] = None, 
                 output_dir: str = "output",
                 prompts_dir: str = "src/prompts"):
        """
        Initialize the AutoCodeSystem.
        
        Args:
            requirements_file: Path to the file containing user requirements (optional)
            output_dir: Directory where output files will be saved
            prompts_dir: Directory containing prompt files
        """
        self.requirements_file = requirements_file
        self.output_dir = output_dir
        self.prompts_dir = prompts_dir
        self.specification_file = os.path.join(output_dir, "specification.json")
        self.generated_code_dir = os.path.join(output_dir, "generated_code")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def process_requirements(self) -> bool:
        """
        Process user requirements into a structured JSON specification.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Processing user requirements...")
        
        # Build command
        cmd = ["python", "src/main.py"]
        if self.requirements_file:
            cmd.extend(["--input", self.requirements_file])
        cmd.extend(["--output", self.specification_file])
        cmd.extend(["--prompts-dir", self.prompts_dir])
        
        # Run command
        try:
            logger.info(f"Running command: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            logger.info(f"Requirements processed successfully. Specification saved to {self.specification_file}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error processing requirements: {e}")
            return False
    
    def generate_code(self) -> bool:
        """
        Generate code based on the JSON specification.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Generating code...")
        
        # Build command
        cmd = ["python", "src/code_generator.py"]
        cmd.extend(["--specification", self.specification_file])
        cmd.extend(["--output", self.generated_code_dir])
        cmd.extend(["--prompts-dir", self.prompts_dir])
        
        # Run command
        try:
            logger.info(f"Running command: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            logger.info(f"Code generated successfully. Output saved to {self.generated_code_dir}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error generating code: {e}")
            return False
    
    def run(self) -> bool:
        """
        Run the entire autonomous code generation process.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Starting autonomous code generation process...")
        
        # Step 1: Process requirements
        if not self.process_requirements():
            logger.error("Failed to process requirements. Aborting.")
            return False
        
        # Step 2: Generate code
        if not self.generate_code():
            logger.error("Failed to generate code. Aborting.")
            return False
        
        logger.info("Autonomous code generation process completed successfully.")
        return True


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Autonomous Code Generation System")
    parser.add_argument("--requirements", "-r", type=str,
                        help="Path to the file containing user requirements")
    parser.add_argument("--output", "-o", type=str, default="output",
                        help="Directory where output files will be saved")
    parser.add_argument("--prompts-dir", "-p", type=str, default="src/prompts",
                        help="Directory containing prompt files")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Run in interactive mode (prompt for requirements)")
    
    args = parser.parse_args()
    
    # If interactive mode is enabled, prompt for requirements
    if args.interactive and not args.requirements:
        requirements_file = os.path.join(args.output, "requirements.txt")
        os.makedirs(os.path.dirname(requirements_file), exist_ok=True)
        
        print("Enter your requirements (Ctrl+D to finish):")
        with open(requirements_file, 'w', encoding='utf-8') as file:
            try:
                while True:
                    line = input()
                    file.write(line + "\n")
            except EOFError:
                pass
        
        args.requirements = requirements_file
    
    # Run the system
    system = AutoCodeSystem(
        requirements_file=args.requirements,
        output_dir=args.output,
        prompts_dir=args.prompts_dir
    )
    
    success = system.run()
    
    if success:
        print("\nCode generation completed successfully!")
        print(f"Generated code is available in: {os.path.abspath(system.generated_code_dir)}")
    else:
        print("\nCode generation failed. Check the logs for details.")
        exit(1)


if __name__ == "__main__":
    main()
