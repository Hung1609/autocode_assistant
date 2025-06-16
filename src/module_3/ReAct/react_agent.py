from typing import List, Dict, Any, Optional, Tuple, Set
import json
import logging
import re
import os
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage

class ReActAgent:
    def __init__(self, llm, tools: List[Any], project_root: str, max_iterations: int = 99, 
                 max_history_length: int = 200, tool_names_with_state: Optional[Set[str]] = None):
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}
        self.project_root = project_root
        self.max_iterations = max_iterations
        self.max_history_length = max_history_length
        self.tool_names_with_state = tool_names_with_state or {"project_structure", "create_run_script", "file_generator"}
        self.logger = logging.getLogger(__name__)
        
        # Validate required tools are available
        required_tools = {"read_design_file", "read_spec_file"}
        missing_tools = required_tools - set(self.tools.keys())
        if missing_tools:
            raise ValueError(f"Missing required tools: {missing_tools}")
        
        # State để theo dõi tiến trình        
        self.state = {
            "design_data": None,
            "spec_data": None,
            "structure_created": False,
            "files_to_generate": [],
            "generated_files": [],
            "validation_result": None,
            "run_script_created": False,
            "run_script_executed": False,
            "history": []
        }
        
    def run(self, task: str) -> str:
        self._add_to_history(f"Task: {task}")
        iteration = 0
        observation = "Task started. You should begin by reading the design and spec files."
        
        while iteration < self.max_iterations:
            iteration += 1
            self.logger.info(f"--- Iteration {iteration}/{self.max_iterations} ---")
            
            # Create prompt and call LLM
            prompt = self._build_prompt(observation)
            self.logger.debug(f"PROMPT FOR LLM:\n{prompt}")
            response_content = self._generate_thought_and_action(prompt)
            
            if not response_content:
                self.logger.error("LLM failed to generate a response. Stopping.")
                return "Critical Error: LLM did not respond."

            # Parse response
            thought, action_name, action_input_str, is_paused, answer = self._parse_response(response_content)
            self._add_to_history(f"Thought: {thought}")
            self.logger.info(f"Thought: {thought}")
            
            if answer:
                self.logger.info(f"Final Answer: {answer}")
                return answer
        
            if not is_paused:
                observation = "Error: Invalid response format. You must end the Action block with PAUSE."
                self.logger.warning(observation)
                continue
            
            if not action_name or action_name not in self.tools:
                observation = f"Error: Invalid action '{action_name}'. Available actions: {list(self.tools.keys())}"
                self.logger.error(observation)
                continue
            
            self._add_to_history(f"Action: {action_name}: {action_input_str}\nPAUSE")
            self.logger.info(f"Action: {action_name}: {action_input_str}")
            
            try:
                # Validate and parse JSON input
                if not action_input_str.strip():
                    action_input_dict = {}
                else:
                    try:
                        action_input_dict = json.loads(action_input_str)
                        if not isinstance(action_input_dict, dict):
                            raise ValueError("Action input must be a JSON object")
                    except json.JSONDecodeError as e:
                        observation = f"Error: Invalid JSON in action input: {e}. Input was: {action_input_str}"
                        self.logger.error(observation)
                        continue
                
                # Add state data to input if tool needs it
                if action_name in self.tool_names_with_state:
                    if self.state["design_data"]:
                        action_input_dict['design_data'] = self.state["design_data"]
                    if self.state["spec_data"]:
                        action_input_dict['spec_data'] = self.state["spec_data"]
                    # Also add project_root for tools that need it
                    action_input_dict['project_root'] = self.project_root
                
                # Execute tool
                tool_to_run = self.tools[action_name]
                observation = tool_to_run._run(**action_input_dict)

                self.logger.info(f"Observation: {observation[:500]}{'...' if len(observation) > 500 else ''}")
                self._add_to_history(f"Observation: {observation}")
                self._update_state(action_name, action_input_dict, observation)
                
            except TypeError as e:
                observation = f"Error: Invalid parameters for action '{action_name}': {e}"
                self.logger.error(observation)
            except Exception as e:
                observation = f"Error executing action '{action_name}': {e}"
                self.logger.error(observation, exc_info=True)
                
        self.logger.warning("Max iterations reached.")
        return "Task failed: Max iterations reached without a final answer."
    
    def _add_to_history(self, entry: str) -> None:
        """Add entry to history and manage maximum length."""
        self.state["history"].append(entry)
        if len(self.state["history"]) > self.max_history_length:
            # Keep the first entry (task description) and recent entries
            self.state["history"] = [self.state["history"][0]] + self.state["history"][-(self.max_history_length-1):]
    
    def _generate_thought_and_action(self, prompt: str) -> Optional[str]:
        try:
            response = self.llm.invoke([
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=prompt)
            ])
            self.logger.debug(f"LLM RAW RESPONSE:\n{response.content.strip()}")
            return response.content.strip()
        except Exception as e:
            self.logger.error(f"Error calling LLM API: {e}")
            return None
        
    def _build_prompt(self, observation: Optional[str]) -> str:
        # Use truncated history to prevent overly long prompts
        history_entries = self.state["history"][-20:] if len(self.state["history"]) > 20 else self.state["history"]
        history_str = "\n".join(history_entries)
        
        # Get tool descriptions with better error handling
        tools_description = []
        for name, tool in self.tools.items():
            try:
                # Try to get args schema safely
                if hasattr(tool, 'get_input_schema'):
                    schema = tool.get_input_schema()
                    if hasattr(schema, 'model_fields'):
                        # Pydantic v2
                        args_str = ", ".join(schema.model_fields.keys())
                    elif hasattr(schema, '__fields__'):
                        # Pydantic v1
                        args_str = ", ".join(schema.__fields__.keys())
                    else:
                        args_str = "Check tool documentation"
                else:
                    args_str = "No schema available"
            except Exception as e:
                self.logger.warning(f"Could not get schema for tool {name}: {e}")
                args_str = "Schema unavailable"
            
            tools_description.append(f"- {name}({args_str}): {tool.description}")
        tools_description_str = "\n".join(tools_description)
        
        state_summary = self.state.copy()
        state_summary.pop('history', None)
        state_summary.pop('design_data', None) # Don't show full data in prompt
        state_summary.pop('spec_data', None)

        return f"""
You are an autonomous software engineering agent. Follow a strict `Thought -> Action -> PAUSE -> Observation` loop.
Your goal is to build a complete software project by following the user's task.

**Current Progress:**
{json.dumps(state_summary, indent=2)}

**Tools Available:**
{tools_description_str}

**Conversation History:**
{history_str}

**Last Observation:**
{observation}

**Your Task:**
Based on the history and the last observation, decide the next logical step.
1.  Think about what you need to do next.
2.  Choose the single best action from the `Tools Available` list.
3.  Format your response STRICTLY as follows, with a JSON object for the input:

Thought: [Your reasoning and plan for the next step.]
Action: [action_name]: {{"parameter_name": "value"}}
PAUSE

Or, if the entire project is built and executed successfully:

Thought: [Your reasoning that the project is complete.]
Answer: [A summary of the result.]
"""
    
    def _get_system_prompt(self) -> str:
        tool_descriptions = []
        for name, tool in self.tools.items():
            try:
                tool_descriptions.append(f"- {name}: {tool.description}")
            except Exception:
                tool_descriptions.append(f"- {name}: Tool available")
        
        tools_list = "\n".join(tool_descriptions)
        
        return f"""
You are an expert software architect following a ReAct framework.
Your job is to generate a complete application based on provided design and specification JSON files.

AVAILABLE TOOLS:
{tools_list}

WORKFLOW:
1. Read the design file using read_design_file
2. Read the spec file using read_spec_file  
3. Create project structure using project_structure
4. Generate files using file_generator (call this for each file in the structure)
5. Validate the project using project_validator
6. Create run script using create_run_script
7. Execute run script using execute_run_script

RESPONSE FORMAT:
You must follow this exact format in each iteration:

Thought: [Explain what you need to do next and why]
Action: [tool_name]: {{"parameter": "value"}}
PAUSE

Wait for the Observation, then continue with the next step.
When completely finished, provide your final response as:
Answer: [Summary of what was accomplished]

IMPORTANT RULES:
- Action inputs must be valid JSON objects
- Always include PAUSE after each Action
- Use the tools in the correct sequence
- Don't skip steps in the workflow
- Each file_generator call should generate ONE specific file
"""
    
    def _parse_response(self, response: str) -> Tuple[str, str, str, bool, Optional[str]]:
        thought = ""
        action_name = ""
        action_input = "{}"
        answer = None

        # Improved regex patterns for better parsing
        thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|Answer:|$)", response, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()

        answer_match = re.search(r"Answer:\s*(.*)", response, re.DOTALL)
        if answer_match:
            answer = answer_match.group(1).strip()
            return thought, action_name, action_input, False, answer

        # Improved action regex to handle multiline JSON better
        action_match = re.search(r"Action:\s*(\w+):\s*(\{.*?\})", response, re.DOTALL)
        if action_match:
            action_name = action_match.group(1).strip()
            action_input = action_match.group(2).strip()

        is_paused = bool(re.search(r'\bPAUSE\b', response))
        
        return thought, action_name, action_input, is_paused, answer
    
    def _is_successful_operation(self, observation: str) -> bool:
        """Check if an operation was successful using multiple indicators."""
        success_indicators = ["successfully", "success", "created", "generated", "completed"]
        error_indicators = ["error", "failed", "exception", "not found"]
        
        observation_lower = observation.lower()
        
        # If any error indicator is found, it's not successful
        if any(error in observation_lower for error in error_indicators):
            return False
            
        # If any success indicator is found, it's successful
        return any(success in observation_lower for success in success_indicators)
    
    def _safe_json_parse(self, text: str) -> Optional[Dict]:
        """Safely parse JSON text with better error handling."""
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON: {e}. Text was: {text[:200]}...")
            return None
    
    def _update_state(self, action: str, action_input: Dict, observation: str):
        """Update agent state with better validation and error handling."""
        try:
            if action == "read_design_file" and self._is_successful_operation(observation):
                parsed_data = self._safe_json_parse(observation)
                if parsed_data:
                    self.state["design_data"] = parsed_data
                    # Safely extract files to generate
                    try:
                        structure = parsed_data.get('folder_Structure', {}).get('structure', [])
                        self.state["files_to_generate"] = [
                            item['path'] for item in structure 
                            if isinstance(item, dict) and 
                               'path' in item and 
                               'directory' not in item.get('description', '').lower()
                        ]
                    except (KeyError, TypeError) as e:
                        self.logger.warning(f"Could not extract file list from design data: {e}")
                        
            elif action == "read_spec_file" and self._is_successful_operation(observation):
                parsed_data = self._safe_json_parse(observation)
                if parsed_data:
                    self.state["spec_data"] = parsed_data
                    
            elif action == "project_structure" and self._is_successful_operation(observation):
                self.state["structure_created"] = True
                
            elif action == "file_generator" and self._is_successful_operation(observation):
                if "file_path" in action_input:
                    try:
                        file_path_rel = str(Path(action_input["file_path"]).relative_to(self.project_root))
                        if file_path_rel not in self.state["generated_files"]:
                            self.state["generated_files"].append(file_path_rel)
                    except (ValueError, KeyError) as e:
                        self.logger.warning(f"Could not process file path: {e}")
                        
            elif action == "project_validator":
                self.state["validation_result"] = observation
                
            elif action == "create_run_script" and self._is_successful_operation(observation):
                self.state["run_script_created"] = True
                
            elif action == "execute_run_script" and self._is_successful_operation(observation):
                self.state["run_script_executed"] = True
                
        except Exception as e:
            self.logger.error(f"Error updating state for action {action}: {e}")
