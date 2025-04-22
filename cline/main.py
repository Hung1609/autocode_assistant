#!/usr/bin/env python3
"""
Autonomous Code Generation System
--------------------------------
This script orchestrates the process of:
1. Extracting information from user requirements
2. Clarifying unclear requirements
3. Structuring information into JSON for code generation
"""

import os
import json
import argparse
from typing import Dict, List, Any, Optional


class RequirementsProcessor:
    """Main class for processing user requirements into structured JSON specifications."""

    def __init__(self, prompts_dir: str = "prompts"):
        """
        Initialize the RequirementsProcessor.
        
        Args:
            prompts_dir: Directory containing the prompt files
        """
        self.prompts_dir = prompts_dir
        self.prompts = self._load_prompts()
        
    def _load_prompts(self) -> Dict[str, str]:
        """
        Load all prompt files from the prompts directory.
        
        Returns:
            Dictionary mapping prompt names to their content
        """
        prompts = {}
        prompt_files = {
            "extraction": "information_extraction_prompt.txt",
            "clarification": "requirement_clarification_prompt.txt",
            "json_structuring": "json_structuring_prompt.txt"
        }
        
        for key, filename in prompt_files.items():
            file_path = os.path.join(self.prompts_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    prompts[key] = file.read()
            except FileNotFoundError:
                print(f"Warning: Prompt file {file_path} not found")
        
        return prompts
    
    def extract_information(self, user_requirements: str) -> Dict[str, Any]:
        """
        Extract structured information from user requirements.
        
        Args:
            user_requirements: Raw user requirements text
            
        Returns:
            Dictionary containing extracted information
        """
        # In a real implementation, this would use an LLM API with the extraction prompt
        print("Extracting information from user requirements...")
        print(f"Using prompt: {self.prompts.get('extraction', 'Extraction prompt not found')[:100]}...")
        
        # Placeholder for extracted information
        # In a real implementation, this would be the output from the LLM
        extracted_info = {
            "project_overview": {
                "purpose": "Example extracted purpose",
                "problem_statement": "Example problem statement",
                "scope": "Example scope"
            },
            "functional_requirements": [
                {"description": "Example functional requirement 1"},
                {"description": "Example functional requirement 2"}
            ],
            "non_functional_requirements": [
                {"description": "Example non-functional requirement 1"}
            ],
            "information_gaps": [
                {"description": "Example information gap 1"}
            ]
        }
        
        return extracted_info
    
    def clarify_requirements(self, extracted_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate clarification questions for unclear requirements.
        
        Args:
            extracted_info: Dictionary containing extracted information
            
        Returns:
            Dictionary containing clarification questions
        """
        # In a real implementation, this would use an LLM API with the clarification prompt
        print("Generating clarification questions...")
        print(f"Using prompt: {self.prompts.get('clarification', 'Clarification prompt not found')[:100]}...")
        
        # Placeholder for clarification questions
        # In a real implementation, this would be the output from the LLM
        clarification_questions = {
            "questions": [
                {
                    "requirement_reference": "Example functional requirement 1",
                    "issue_type": "Ambiguity",
                    "severity": "High",
                    "question": "Example clarification question 1?",
                    "potential_options": ["Option 1", "Option 2"],
                    "impact": "Example impact description"
                },
                {
                    "requirement_reference": "Example non-functional requirement 1",
                    "issue_type": "Incompleteness",
                    "severity": "Medium",
                    "question": "Example clarification question 2?",
                    "potential_options": ["Option A", "Option B"],
                    "impact": "Example impact description"
                }
            ]
        }
        
        return clarification_questions
    
    def get_clarification_answers(self, clarification_questions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate getting answers to clarification questions.
        In a real implementation, this would involve user interaction.
        
        Args:
            clarification_questions: Dictionary containing clarification questions
            
        Returns:
            Dictionary containing answers to clarification questions
        """
        print("Getting answers to clarification questions...")
        
        # Placeholder for clarification answers
        # In a real implementation, this would come from user interaction
        clarification_answers = {
            "answers": [
                {
                    "question": "Example clarification question 1?",
                    "answer": "Example answer 1"
                },
                {
                    "question": "Example clarification question 2?",
                    "answer": "Example answer 2"
                }
            ]
        }
        
        return clarification_answers
    
    def structure_to_json(self, 
                          extracted_info: Dict[str, Any], 
                          clarification_answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure the extracted and clarified information into a JSON specification.
        
        Args:
            extracted_info: Dictionary containing extracted information
            clarification_answers: Dictionary containing answers to clarification questions
            
        Returns:
            Dictionary containing the structured JSON specification
        """
        # In a real implementation, this would use an LLM API with the JSON structuring prompt
        print("Structuring information into JSON specification...")
        print(f"Using prompt: {self.prompts.get('json_structuring', 'JSON structuring prompt not found')[:100]}...")
        
        # Placeholder for JSON specification
        # In a real implementation, this would be the output from the LLM
        json_specification = {
            "metadata": {
                "projectName": "Example Project",
                "version": "0.1.0",
                "lastUpdated": "2025-04-14T08:00:00Z",
                "authors": ["Autonomous System"],
                "status": "Draft"
            },
            "systemOverview": {
                "purpose": "Example extracted purpose",
                "scope": "Example scope",
                "targetUsers": ["Example user 1", "Example user 2"],
                "keyFeatures": ["Example feature 1", "Example feature 2"]
            },
            "functionalRequirements": [
                {
                    "id": "FR-001",
                    "title": "Example Requirement 1",
                    "description": "Example functional requirement 1",
                    "priority": "high",
                    "status": "approved",
                    "source": "user requirements",
                    "dependencies": [],
                    "acceptanceCriteria": ["Example criterion 1", "Example criterion 2"],
                    "notes": "Example notes"
                },
                {
                    "id": "FR-002",
                    "title": "Example Requirement 2",
                    "description": "Example functional requirement 2",
                    "priority": "medium",
                    "status": "approved",
                    "source": "user requirements",
                    "dependencies": ["FR-001"],
                    "acceptanceCriteria": ["Example criterion 1"],
                    "notes": ""
                }
            ],
            "nonFunctionalRequirements": [
                {
                    "id": "NFR-001",
                    "category": "performance",
                    "title": "Example Non-Functional Requirement",
                    "description": "Example non-functional requirement 1",
                    "priority": "high",
                    "metrics": [
                        {
                            "name": "response time",
                            "value": "200",
                            "unit": "ms"
                        }
                    ],
                    "status": "approved",
                    "dependencies": [],
                    "notes": ""
                }
            ]
        }
        
        return json_specification
    
    def save_json_specification(self, json_specification: Dict[str, Any], output_file: str) -> None:
        """
        Save the JSON specification to a file.
        
        Args:
            json_specification: Dictionary containing the structured JSON specification
            output_file: Path to the output file
        """
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(json_specification, file, indent=2)
            
        print(f"JSON specification saved to {output_file}")
    
    def process_requirements(self, user_requirements: str, output_file: str) -> Dict[str, Any]:
        """
        Process user requirements into a structured JSON specification.
        
        Args:
            user_requirements: Raw user requirements text
            output_file: Path to the output file
            
        Returns:
            Dictionary containing the structured JSON specification
        """
        # Step 1: Extract information from user requirements
        extracted_info = self.extract_information(user_requirements)
        
        # Step 2: Generate clarification questions
        clarification_questions = self.clarify_requirements(extracted_info)
        
        # Step 3: Get answers to clarification questions
        clarification_answers = self.get_clarification_answers(clarification_questions)
        
        # Step 4: Structure information into JSON
        json_specification = self.structure_to_json(extracted_info, clarification_answers)
        
        # Step 5: Save JSON specification to file
        self.save_json_specification(json_specification, output_file)
        
        return json_specification


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Process user requirements into structured JSON specifications")
    parser.add_argument("--input", "-i", type=str, help="Path to the input file containing user requirements")
    parser.add_argument("--output", "-o", type=str, default="output/specification.json", 
                        help="Path to the output JSON specification file")
    parser.add_argument("--prompts-dir", "-p", type=str, default="prompts",
                        help="Directory containing the prompt files")
    
    args = parser.parse_args()
    
    # Get user requirements from file or stdin
    if args.input:
        with open(args.input, 'r', encoding='utf-8') as file:
            user_requirements = file.read()
    else:
        print("Enter user requirements (Ctrl+D to finish):")
        user_requirements = ""
        try:
            while True:
                line = input()
                user_requirements += line + "\n"
        except EOFError:
            pass
    
    # Process user requirements
    processor = RequirementsProcessor(prompts_dir=args.prompts_dir)
    processor.process_requirements(user_requirements, args.output)


if __name__ == "__main__":
    main()
