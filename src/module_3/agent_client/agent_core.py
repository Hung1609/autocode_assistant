# this file is responsible for the main logic of the agent: calling LLM, handling tool requests, and interacting with the MCP server.

import google.generativeai as genai
from google.generativeai import protos as gap
import os
import dotenv
import requests
import json
import argparse
import logging
from copy import deepcopy
from tools_definition import get_tool_definitions

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
dotenv.load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MCP_SERVER_URL = "http://127.0.0.1:5100"
MODEL_NAME = "gemini-2.0-flash"

genai.configure(api_key=API_KEY)
TOOL_DEFINITIONS = get_tool_definitions()
# **NEED TO IMPROVE LATER, RIGHT NOW, THE CONTENT FOCUSES ON DIRECT THE AGENT TO INTERACT WITH FILE SYSTEM**
# FUTURE IMPROVEMENTS NEED TO INCLUDE INSTRUCTIONS FOR CREATE JSON FILE AND GENEREATE CODE
# ALSO NEED TO INSTRUCT THE AGENT HOW TO INTEPRET AND RESPOND ERROR FROM api_result TO THE USER IN A FRIENDLY WAY
SYSTEM_INSTRUCTION = """You are an AI assistant integrated into a development environment.
Your primary function is to help users by interacting with their project files using the available tools.
You can create files, read files, list directory contents, create directories, and edit files within the user's designated project workspace.
Always use the provided tools when a file system operation is required.
When listing files, present the results clearly.
When editing files, remember that the current implementation replaces the entire file content.
Confirm successful operations concisely. If an operation fails, report the error message provided.
Do not attempt operations outside the user's workspace.
Base all relative paths on the root of the user's provided workspace path.
"""

model = genai.GenerativeModel(
    MODEL_NAME,
    system_instruction=SYSTEM_INSTRUCTION,
    tools=TOOL_DEFINITIONS
)
logging.info(f"Model '{MODEL_NAME}' configured with tools.")

def call_mcp_tool(tool_name: str, parameters: dict, workspace_path: str) -> dict:
    target_url = f"{MCP_SERVER_URL}/tools/{tool_name}"
    payload = parameters.copy()
    payload["workspace_path"] = workspace_path

    logging.info(f"Calling MCP tool '{tool_name}' at {target_url} for workspace '{os.path.basename(workspace_path)}'")
    logging.debug(f"MCP Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(target_url, json=payload, timeout=30) # can increase timeout
        response.raise_for_status()
        mcp_result = response.json()
        logging.info(f"MCP tool '{tool_name}' executed. Result status: {mcp_result.get('status')}")
        logging.debug(f"MCP Result: {json.dumps(mcp_result, indent=2)}")
        return mcp_result

    except requests.exceptions.Timeout:
        logging.error(f"Timeout calling MCP server tool '{tool_name}' at {target_url}")
        return {"status": "error", "message": "The tool execution server timed out."}
    except requests.exceptions.ConnectionError:
        logging.error(f"Connection error calling MCP server tool '{tool_name}' at {target_url}. Is the server running?")
        return {"status": "error", "message": "Could not connect to the tool execution server. Please ensure it's running."}
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error calling MCP server tool '{tool_name}': {e.response.status_code} {e.response.reason}")
        try:
            # Try to parse error details from server response if available
            error_details = e.response.json()
            return error_details # Return the error structure from the server
        except json.JSONDecodeError:
            return {"status": "error", "message": f"Tool execution failed with HTTP status {e.response.status_code}. No details available."}
    except requests.exceptions.RequestException as e:
        logging.exception(f"Error during request to MCP server tool '{tool_name}': {e}")
        return {"status": "error", "message": f"An unexpected error occurred while communicating with the tool server: {e}"}
    except json.JSONDecodeError:
         logging.error(f"Could not decode JSON response from MCP server tool '{tool_name}'. Response text: {response.text[:100]}...")
         return {"status": "error", "message": "Received an invalid response from the tool execution server."} 

# Agent logic
# RIGHT NOW, THE AGENT IS DESIGNED TO RUN IN A SINGLE TURN ONLY --> NEED TO IMPROVE TO CALL TOOL MULTIPLE TIMES
# IN THE FUTURE, THE AGENT SHOULD BE ABLE TO HANDLE MULTIPLE TURNS, NEED TO MAINTAIN history thoroughout the run_agent_turn
def run_agent_turn(user_prompt: str, workspace_path: str, current_history: list = None, generation_config_override: dict = None):
    logging.info(f"Starting agent turn. Workspace: '{os.path.basename(workspace_path)}', Prompt: '{user_prompt[:100]}...'")
    result_package = {
        "final_llm_text_response": None,
        "last_tool_name_called": None,
        "last_tool_arguments": None,
        "last_tool_mcp_result": None,
        "error": False,
        "error_message": None,
        "full_history": []
    }
    if not workspace_path or not os.path.isdir(workspace_path):
        msg = f"Invalid or inaccessible workspace path provided: '{workspace_path}'"
        logging.error(msg)
        result_package["error"] = True
        result_package["error_message"] = msg
        result_package["final_llm_text_response"] = f"Error: {msg}"
        return result_package

    initial_chat_history = []
    if current_history:
        initial_chat_history = deepcopy(current_history)
        logger.debug(f"AgentCore: Continuing with provided history of {len(initial_chat_history)} messages.")

    default_gen_config = {
        "temperature": 0.7,
        "max_output_tokens": 15000,
        "top_p": 0.95
    }
    if generation_config_override:
        default_gen_config.update(generation_config_override)
    effective_gen_config = genai.types.GenerationConfig(**default_gen_config)
    logger.debug(f"AgentCore: Using generation config: {effective_gen_config}")

    try:
        chat = model.start_chat(history=initial_chat_history)

        logger.debug(f"AgentCore: Sending user message to chat: '{user_prompt[:100]}...'")
        response = chat.send_message(
            content = user_prompt,
            generation_config = effective_gen_config,
            stream = True
        )
        response.resolve()
        logger.debug(f"AgentCore: Initial model response received. History length: {len(chat.history)}")

        while True:
            if not response.candidates or not response.candidates[0].content:
                logger.error("AgentCore: Invalid response structure from model (no candidates or parts).")
                result_package["error"] = True
                result_package["error_message"] = "AI returned an invalid response structure."
                result_package["final_llm_text_response"] = result_package["error_message"]
                break

            function_call_part = None
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call.name:
                    function_call_part = part
                    break

            if function_call_part:
                fc = function_call_part.function_call
                tool_name = fc.name
                tool_args = {key: value for key, value in fc.args.items()}
                logger.info(f"AgentCore: Gemini requested tool: '{tool_name}' with args: {tool_args}")
                result_package["last_tool_name_called"] = tool_name
                result_package["last_tool_arguments"] = tool_args
                mcp_response_data = call_mcp_tool(tool_name, tool_args, workspace_path)
                result_package["last_tool_mcp_result"] = mcp_response_data

                if mcp_response_data.get("status") == "error":
                    logger.warning(f"AgentCore: MCP tool '{tool_name}' failed. Result: {mcp_response_data}")
                logger.debug(f"AgentCore: Sending function response for '{tool_name}' back to model.")

                
                # function_response=genai.types.FunctionResponse(
                #     name=tool_name,
                #     response=mcp_response_data
                # )
                
                response = chat.send_message(
                    content=[ 
                        gap.Part(function_response=gap.FunctionResponse( 
                            name=tool_name,
                            response=mcp_response_data
                        ))
                    ],
                    generation_config=effective_gen_config
                )
                response.resolve()
                logger.debug(f"AgentCore: Response received after sending tool result for '{tool_name}'. History length: {len(chat.history)}")
            else:
                final_text_accumulated = "".join(p.text for p in response.candidates[0].content.parts if hasattr(p, 'text'))
                result_package["final_llm_text_response"] = final_text_accumulated.strip()
                logger.info(f"AgentCore: No more function calls. Final LLM text: '{result_package['final_llm_text_response'][:100]}...'")
                break
    except Exception as e:
        logger.exception("AgentCore: An unexpected error occurred during the agent turn.")
        error_msg = f"Sorry, an unexpected error occurred in AgentCore: {str(e)}"
        if hasattr(e, 'message') and e.message:
             error_msg = f"Sorry, an API or AgentCore error occurred: {e.message}"
        
        result_package["error"] = True
        result_package["error_message"] = error_msg
        result_package["final_llm_text_response"] = error_msg

    if 'chat' in locals() and chat.history:
        serializable_history = []
        for content_message in chat.history:
            parts_list = []
            for part_proto in content_message.parts:
                if part_proto.text:
                    parts_list.append({"text": part_proto.text})
                elif hasattr(part_proto, 'function_call') and part_proto.function_call.name:
                    fc_args = {key: value for key, value in part_proto.function_call.args.items()}
                    parts_list.append({"function_call": {"name": part_proto.function_call.name, "args": fc_args}})
                elif hasattr(part_proto, 'function_response') and part_proto.function_response.name:
                    parts_list.append({"function_response": {"name": part_proto.function_response.name, "response": dict(part_proto.function_response.response)}})
            serializable_history.append({"role": content_message.role, "parts": parts_list})
        result_package["full_history"] = serializable_history
    elif not result_package["full_history"] and initial_chat_history:
        result_package["full_history"] = initial_chat_history
        if not any(p.get("text") == user_prompt for entry in initial_chat_history if entry["role"] == "user" for p in entry["parts"]):
             result_package["full_history"].append({"role": "user", "parts": [{"text": user_prompt}]})

    logger.info(f"AgentCore: Turn finished. Error: {result_package['error']}. LLM Text: '{str(result_package['final_llm_text_response'])[:100]}...'")
    return result_package

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Agent Client Turn")
    parser.add_argument("--prompt", required=True, help="User prompt for the agent")
    parser.add_argument("--workspace", required=True, help="Absolute path to the project workspace")
    args = parser.parse_args()

    result_dict = run_agent_turn(args.prompt, args.workspace) 
    
    try:
        print(json.dumps(result_dict))
    except TypeError as e:
        # (ví dụ: đối tượng Part của Gemini nếu không được chuyển đổi đúng)
        logger.error(f"AgentCore: Could not serialize result_dict to JSON: {e}. Result: {result_dict}")
        fallback_result = {
            "final_llm_text_response": "Error: Could not serialize agent result.",
            "last_tool_name_called": result_dict.get("last_tool_name_called"),
            "last_tool_arguments": result_dict.get("last_tool_arguments"),
            "last_tool_mcp_result": result_dict.get("last_tool_mcp_result"),
            "error": True,
            "error_message": f"Internal serialization error: {e}",
            "full_history": [] #
        }
        print(json.dumps(fallback_result))









#     history = [{"role": "user", "parts": [user_prompt]}]

#     try:
#         logging.debug("Sending initial prompt to model.generate_content")
#         response = model.generate_content(
#             contents=history,
#             generation_config=genai.types.GenerationConfig(
#                 temperature=1,
#                 max_output_tokens=10000,
#                 top_p=0.95
#             )
#         )
#         logging.debug("Model response received.")

#         response_part = response.candidates[0].content.parts[0]

#         while hasattr(response_part, 'function_call') and response_part.function_call.name:
#             function_call = response_part.function_call
#             tool_name = function_call.name
#             tool_args = {key: value for key, value in function_call.args.items()}

#             logging.info(f"Gemini requested tool: '{tool_name}' with args: {tool_args}")

#             # Call the MCP server
#             api_result = call_mcp_tool(tool_name, tool_args, workspace_path)

#             # Append the function call and response to history with correct roles
#             history.append({
#                 "role": "model",
#                 "parts": [{
#                     "function_call": {
#                         "name": tool_name,
#                         "args": tool_args
#                     }
#                 }]
#             })

#             history.append({
#                 "role": "user",  # NEED TO REVISE, THE ROLE CAN BE TOOL OR FUNCTION BASED ON THE API GEMINI
#                 "parts": [{
#                     "function_response": {
#                         "name": tool_name,        # The name of the function that was called
#                         "response": api_result,   # The actual dictionary returned by call_mcp_tool
#                     }
#                 }]
#             })

#             # Make the next call to LLM with updated history
#             logging.debug("Sending function response back to model.generate_content")
#             response = model.generate_content(
#                 contents=history,
#                 generation_config=genai.types.GenerationConfig(
#                     temperature=1,
#                     max_output_tokens=10000,
#                     top_p=0.95
#                 )
#             )
#             logging.debug("Response received after sending tool result.")
#             response_part = response.candidates[0].content.parts[0]

#         # No more function calls
#         if hasattr(response_part, 'text'):
#             final_text_response = response_part.text
#             logging.info(f"Agent turn finished. Final Response: '{final_text_response[:100]}...'")
#             return final_text_response
#         else:
#             logging.error("Loop exited but final response part is not text.")
#             logging.debug(f"Final response part: {response_part}")
#             return "Sorry, I received an unexpected final response structure from the AI."

#     except Exception as e:
#         logging.exception("An unexpected error occurred during the agent turn.")
#         if hasattr(e, 'message'):
#              return f"Sorry, an API error occurred: {e.message}"
#         return f"Sorry, an unexpected error occurred while processing your request: {e}"

# # --- Command-Line Execution for Testing ---
# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Run Agent Client Turn")
#     parser.add_argument("--prompt", required=True, help="User prompt for the agent")
#     parser.add_argument("--workspace", required=True, help="Absolute path to the project workspace")
#     args = parser.parse_args()

#     # Run the agent turn
#     final_result = run_agent_turn(args.prompt, args.workspace)

#     # Print ONLY the final result to stdout for the extension to capture
#     print(final_result)