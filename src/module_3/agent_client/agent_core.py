import google.generativeai as genai
import os
import dotenv
import requests
import json
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from tools_definition import get_tool_definitions

dotenv.load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:5100")
MODEL_NAME = "gemini-2.5-pro-exp-03-25"

if not API_KEY:
    logging.error("GEMINI_API_KEY not found in .env file.")
    exit(1)
try:
    genai.configure(api_key=API_KEY)
    TOOL_DEFINITIONS = get_tool_definitions() # định dạng này không hỗ trợ cho SDK của google
    # cần improve prompt này sau
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
except Exception as e:
    logging.exception(f"Error configuring model: {e}")
    exit(1)

def call_mcp_tool(tool_name, parameters, workspace_path):
    target_url = f"{MCP_SERVER_URL}/tools/{tool_name}"
    payload = parameters.copy()
    payload["workspace_path"] = workspace_path # workspace context

    logging.info(f"Calling MCP tool '{tool_name}' at {target_url} with workspace '{workspace_path}'")
    logging.debug(f"Payload: {payload}")

    try:
        response = requests.post(target_url, json=payload, timeout=20) # can increase timeout
        response.raise_for_status()
        mcp_result = response.json()
        logging.info(f"MCP tool '{tool_name}' executed. Result status: {mcp_result.get('status')}")
        logging.debug(f"MCP Result: {mcp_result}")
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

def run_agent_turn(user_prompt, workspace_path):
    """Runs a single turn of the conversation with the Gemini model."""
    logging.info(f"Starting agent turn. Workspace: '{workspace_path}', Prompt: '{user_prompt[:100]}...'")
    if not workspace_path or not os.path.isdir(workspace_path):
         logging.error(f"Invalid workspace path provided: '{workspace_path}'")
         # Return error directly if workspace isn't valid before calling LLM
         return "Error: Invalid or inaccessible workspace path provided. Please ensure the path exists and is accessible."

    try:
        # Start a chat session (maintains context implicitly if needed, though tool calls reset it somewhat)
        convo = model.start_chat(enable_automatic_function_calling=False) # We handle calls manually

        # Send the user prompt
        response = convo.send_message(user_prompt)
        logging.debug("Initial response received from Gemini.")

        # Loop to handle potential multiple function calls
        while response.candidates[0].content.parts[0].function_call.name:
            function_call = response.candidates[0].content.parts[0].function_call
            tool_name = function_call.name
            tool_args = {key: value for key, value in function_call.args.items()} # Convert FunctionCall args to dict

            logging.info(f"Gemini requested tool: '{tool_name}' with args: {tool_args}")

            # Call the MCP server
            api_result = call_mcp_tool(tool_name, tool_args, workspace_path)

            # Send the tool result back to Gemini
            logging.debug(f"Sending tool result back to Gemini: {api_result}")
            response = convo.send_message(
                genai.types.FunctionResponse(name=tool_name, response=api_result)
            )
            logging.debug("Response received after sending tool result.")

        # Once the loop finishes, the response should be the final text answer
        final_text_response = response.text
        logging.info(f"Agent turn finished. Final Response: '{final_text_response[:100]}...'")
        return final_text_response

    except Exception as e:
        logging.exception("An unexpected error occurred during the agent turn.")
        # Provide a user-friendly error message
        return f"Sorry, an unexpected error occurred while processing your request: {e}"

# --- Command-Line Execution for Testing ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Agent Client Turn")
    parser.add_argument("--prompt", required=True, help="User prompt for the agent")
    parser.add_argument("--workspace", required=True, help="Absolute path to the project workspace")
    args = parser.parse_args()

    # Run the agent turn
    final_result = run_agent_turn(args.prompt, args.workspace)

    # Print ONLY the final result to stdout for the extension to capture
    print(final_result)