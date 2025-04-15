"""
This module contains data models and business logic for the application.
"""

import json
from datetime import datetime
import streamlit as st

from .config import get_gemini_model
from .prompts import SPECIFICATION_PROMPT, CLARIFICATION_PROMPT

class SpecificationGenerator:
    """
    Class responsible for generating software specifications.
    """
    
    def __init__(self, model_name='gemini-2.0-flash'):
        """
        Initialize the specification generator.
        
        Args:
            model_name (str, optional): The name of the model to use. Defaults to 'gemini-2.0-flash'.
        """
        self.model = get_gemini_model(model_name)
    
    def generate_spec(self, user_description, prompt_template=None):
        """
        Generate a specification based on a user description.
        
        Args:
            user_description (str): The user's description of the software requirements.
            prompt_template (str, optional): The prompt template to use. Defaults to None.
            
        Returns:
            dict: The generated specification, or None if an error occurred.
        """
        try:
            if prompt_template is None:
                prompt_template = SPECIFICATION_PROMPT
                
            full_prompt = prompt_template.format(user_description=user_description)
            response = self.model.generate_content(full_prompt)
            
            # Parse JSON response
            try:
                response_text = response.text
                if "```json" in response_text:
                    json_text = response_text.split("```json")[1].split("```")[0].strip()
                    result = json.loads(json_text)
                else:
                    result = json.loads(response_text)
                
                # Ensure project_name exists
                if "project_name" not in result:
                    result["project_name"] = "unnamed_project"
                    
                # Add metadata
                result["metadata"] = {
                    "timestamp": datetime.now().isoformat(),
                    "chosen_model": "gemini-2.0-flash",
                    "original_description": user_description
                }
                
                # Automatically clarify assumptions and questions
                result, clarification_log = self.auto_clarify_assumptions_questions(result)
                
                # Add clarification log to metadata
                if clarification_log:
                    result["metadata"]["clarification_log"] = clarification_log
                
                return result
                
            except json.JSONDecodeError as e:
                st.error(f"Error parsing JSON response: {str(e)}")
                return None
        
        except Exception as e:
            st.error(f"Error generating specification: {str(e)}")
            return None
    
    def auto_clarify_assumptions_questions(self, spec_data):
        """
        Automatically clarify assumptions and answer questions in the specification.
        
        Args:
            spec_data (dict): The specification data.
            
        Returns:
            tuple: A tuple containing the updated specification and a log of clarifications.
        """
        try:
            # Extract assumptions and questions from the initial spec
            assumptions = spec_data.get("assumptions", [])
            questions = spec_data.get("open_questions", [])
            
            if not assumptions and not questions:
                return spec_data, []  # Nothing to clarify
            
            # Format the clarification prompt
            formatted_prompt = CLARIFICATION_PROMPT.format(
                project_name=spec_data.get("project_name", "Unnamed Project"),
                overview=spec_data.get("overview", "No overview provided"),
                assumptions="\n".join([f"- {a}" for a in assumptions]) if assumptions else "None",
                questions="\n".join([f"- {q}" for q in questions]) if questions else "None"
            )
            
            # Get clarifications from the model
            response = self.model.generate_content(formatted_prompt)
            
            # Parse the response
            response_text = response.text
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0].strip()
                clarifications = json.loads(json_text)
            else:
                clarifications = json.loads(response_text)
            
            # Create a log of all clarifications made
            clarification_log = []
            
            # Update assumptions with clarifications
            updated_assumptions = []
            for i, assumption in enumerate(assumptions):
                if i < len(clarifications.get("clarified_assumptions", [])):
                    clarification = clarifications["clarified_assumptions"][i]
                    
                    # Log the clarification
                    clarification_log.append(f"Assumption: '{assumption}' - {clarification['clarification']}")
                    
                    if clarification.get("is_reasonable", True):
                        # Keep the original assumption but add justification
                        updated_assumptions.append(f"{assumption} (Justified: {clarification['clarification']})")
                    else:
                        # Replace with the alternative assumption
                        updated_assumptions.append(f"{clarification['clarification']} (Replaced original: {assumption})")
                else:
                    updated_assumptions.append(assumption)
            
            # Update questions with answers
            resolved_questions = []
            remaining_questions = []
            
            for i, question in enumerate(questions):
                if i < len(clarifications.get("answered_questions", [])):
                    answer = clarifications["answered_questions"][i]
                    
                    # Log the answer
                    confidence = answer.get("confidence", "Medium")
                    clarification_log.append(f"Question: '{question}' - Answered with {confidence} confidence: {answer['answer']}")
                    
                    # Add to resolved questions
                    resolved_questions.append({
                        "question": question,
                        "answer": answer['answer'],
                        "confidence": confidence
                    })
                else:
                    remaining_questions.append(question)
            
            # Update the specification with clarified information
            updated_spec = spec_data.copy()
            updated_spec["assumptions"] = updated_assumptions
            updated_spec["open_questions"] = remaining_questions
            
            # Add resolved questions to the spec
            if resolved_questions:
                updated_spec["resolved_questions"] = resolved_questions
            
            # Add clarification metadata
            if "metadata" not in updated_spec:
                updated_spec["metadata"] = {}
            
            updated_spec["metadata"]["auto_clarification"] = {
                "timestamp": datetime.now().isoformat(),
                "assumptions_clarified": len(clarifications.get("clarified_assumptions", [])),
                "questions_answered": len(clarifications.get("answered_questions", []))
            }
            
            return updated_spec, clarification_log
            
        except Exception as e:
            st.error(f"Error during automatic clarification: {str(e)}")
            return spec_data, [f"Error during clarification: {str(e)}"]
