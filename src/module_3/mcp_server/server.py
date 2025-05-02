from flask import Flask, request, jsonify
import logging
import os
import json # Ensure json is imported for parsing later if needed
import traceback # For logging detailed errors in debug route

# Use relative imports for modules within the mcp_server package
from . import execution
from .execution import execute_generate_design_json, execute_generate_specification_json

# Import necessities for the debug route
try:
    from .config import get_gemini_model
    from .prompts import SPECIFICATION_PROMPT
    # Import necessary type for explicit GenerationConfig if testing that
    # from google.generativeai.types import GenerationConfig
except ImportError as e:
     logging.error(f"FATAL: Failed to import required modules for server or debug route: {e}")
     # Define placeholders to allow Flask to at least load the file, but routes will fail
     def get_gemini_model(model_name): raise NotImplementedError("Config module missing")
     SPECIFICATION_PROMPT = "Debug prompt: {user_description}"


# --- Standard Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Get logger instance for consistent logging
app = Flask(__name__)

# --- Helper Function ---
def get_request_data():
    """Gets JSON data and validates common required fields."""
    if not request.is_json:
        return None, jsonify({"status": "error", "message": "Request must be JSON"}), 400

    data = request.get_json()
    workspace_path = data.get('workspace_path')
    # Note: 'path' is extracted here but might not be needed by all tools directly using this helper
    # relative_path = data.get('path')

    if not workspace_path:
        # Log the missing key for easier debugging
        logger.warning(f"Request rejected: Missing 'workspace_path' in JSON body. Received keys: {list(data.keys())}")
        return None, jsonify({"status": "error", "message": "Missing required parameter: workspace_path"}), 400

    # Return data dictionary and None for error response/status code if validation passed so far
    return data, None, None

# --- Standard Tool API Endpoints ---

@app.route('/tools/create_file', methods=['POST'])
def handle_create_file():
    data, error_response, status_code = get_request_data()
    if error_response:
        return error_response, status_code

    relative_path = data.get('path')
    content = data.get('content')
    workspace_path = data.get('workspace_path') # Already checked by helper

    if relative_path is None or content is None:
        return jsonify({"status": "error", "message": "Missing required parameters: path, content"}), 400

    try:
        # Assuming execution.create_file exists and works as intended
        result = execution.create_file(workspace_path, relative_path, content)
        if result["status"] == "error":
            if "Path resolution outside allowed workspace" in result.get("message","") or "Security Violation" in result.get("message",""):
                http_status = 403
            elif "not found" in result.get("message","").lower() or "is not a valid directory" in result.get("message",""):
                http_status = 404
            else:
                http_status = 500
            return jsonify(result), http_status
        else:
             return jsonify(result), 200
    except AttributeError:
         logger.exception("Error: execution module might be missing 'create_file' function.")
         return jsonify({"status": "error", "message": "Internal server configuration error."}), 500
    except Exception as e:
        logger.exception("Unhandled exception in /tools/create_file")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

# (Add routes for handle_read_file, handle_list_files, handle_create_directory, handle_edit_file - similar structure as before)
# Ensure they call functions from the imported 'execution' module, e.g., execution.read_file(...)

# --- Example structure for others (ensure functions exist in execution.py) ---
@app.route('/tools/read_file', methods=['POST'])
def handle_read_file():
    data, error_response, status_code = get_request_data()
    if error_response: return error_response, status_code
    relative_path = data.get('path')
    workspace_path = data.get('workspace_path')
    if relative_path is None: return jsonify({"status": "error", "message": "Missing required parameter: path"}), 400
    try:
        result = execution.read_file(workspace_path, relative_path) # Call function from execution
        # ... (status code logic same as create_file) ...
        if result.get("status") == "error": http_status=500 # Simplified example
        else: http_status=200
        return jsonify(result), http_status
    except Exception as e: # Catch-all
        logger.exception(f"Unhandled exception in {request.path}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/tools/list_files', methods=['POST'])
def handle_list_files():
    data, error_response, status_code = get_request_data()
    if error_response: return error_response, status_code
    relative_path = data.get('path', "")
    workspace_path = data.get('workspace_path')
    try:
        result = execution.list_files(workspace_path, relative_path) # Call function from execution
        # ... (status code logic) ...
        if result.get("status") == "error": http_status=500
        else: http_status=200
        return jsonify(result), http_status
    except Exception as e:
        logger.exception(f"Unhandled exception in {request.path}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/tools/create_directory', methods=['POST'])
def handle_create_directory():
    data, error_response, status_code = get_request_data()
    if error_response: return error_response, status_code
    relative_path = data.get('path')
    workspace_path = data.get('workspace_path')
    if relative_path is None: return jsonify({"status": "error", "message": "Missing required parameter: path"}), 400
    try:
        result = execution.create_directory(workspace_path, relative_path) # Call function from execution
        # ... (status code logic) ...
        if result.get("status") == "error": http_status=500
        else: http_status=200
        return jsonify(result), http_status
    except Exception as e:
        logger.exception(f"Unhandled exception in {request.path}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/tools/edit_file', methods=['POST'])
def handle_edit_file():
    data, error_response, status_code = get_request_data()
    if error_response: return error_response, status_code
    relative_path = data.get('path')
    changes = data.get('changes_description')
    workspace_path = data.get('workspace_path')
    if relative_path is None or changes is None: return jsonify({"status": "error", "message": "Missing required parameters: path, changes_description"}), 400
    try:
        result = execution.edit_file(workspace_path, relative_path, changes) # Call function from execution
        # ... (status code logic) ...
        if result.get("status") == "error": http_status=500
        else: http_status=200
        return jsonify(result), http_status
    except Exception as e:
        logger.exception(f"Unhandled exception in {request.path}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500
# --- End standard routes ---


# --- Routes for New Generation Tools ---

@app.route('/tools/generate_specification_json', methods=['POST'])
def handle_generate_specification():
    data, error_response, status_code = get_request_data()
    if error_response:
        return error_response, status_code

    project_description = data.get('project_description')
    output_filename_base = data.get('output_filename_base') # Optional
    workspace_path = data.get('workspace_path') # Already checked by helper

    if not project_description:
         return jsonify({"status": "error", "message": "Missing required parameter: project_description"}), 400

    try:
        # Call the execution function (ensure it's imported correctly)
        result = execute_generate_specification_json(workspace_path, project_description, output_filename_base)

        # Determine status code based on result
        if result.get("status") == "error": # Use .get for safety
             http_status = 500 # Default to internal server error for now
             if "SecurityError" in result.get("message", "") or "Path resolution outside" in result.get("message",""):
                 http_status = 403
             elif "Failed to generate" in result.get("message", "") or "Parsing Error" in result.get("message", "") or "generation:" in result.get("message", ""):
                 # Treat generation/parsing issues as server-side problems
                 http_status = 500
             # Add more specific checks if needed based on error messages from execution
             return jsonify(result), http_status
        else:
             return jsonify(result), 200 # OK for success (file path returned in result)
    except Exception as e:
        # Catch errors that might occur *within this handler* itself
        logger.exception("Unhandled exception in /tools/generate_specification_json route handler")
        return jsonify({"status": "error", "message": "Internal server error during spec generation processing"}), 500


@app.route('/tools/generate_design_json', methods=['POST'])
def handle_generate_design():
    data, error_response, status_code = get_request_data() # Uses existing helper
    if error_response:
        return error_response, status_code

    spec_file_path = data.get('spec_file_path')
    workspace_path = data.get('workspace_path') # Already checked by helper

    if not spec_file_path:
         return jsonify({"status": "error", "message": "Missing required parameter: spec_file_path"}), 400

    try:
        # Call the execution function (ensure it's imported correctly)
        result = execute_generate_design_json(workspace_path, spec_file_path)

        # Determine status code based on result
        if result.get("status") == "error":
             http_status = 500
             if "SecurityError" in result.get("message", "") or "Path resolution outside" in result.get("message",""):
                 http_status = 403
             elif "Could not load or parse specification data" in result.get("message", "") or "not found" in result.get("message","").lower():
                  http_status = 404 # Spec file not found
             elif "Failed to generate" in result.get("message", "") or "Parsing Error" in result.get("message","") or "design generation:" in result.get("message", ""):
                  # Treat generation/parsing issues as server-side problems
                  http_status = 500
             return jsonify(result), http_status
        else:
             return jsonify(result), 200 # OK for success
    except Exception as e:
        logger.exception("Unhandled exception in /tools/generate_design_json route handler")
        return jsonify({"status": "error", "message": "Internal server error during design generation processing"}), 500


# --- TEMPORARY DEBUG ROUTE ---
# @app.route('/debug-gemini-spec', methods=['GET'])
# def debug_gemini_spec_call():
#     logger.info("--- DEBUG ROUTE: /debug-gemini-spec accessed ---")
#     try:
#         # 1. Get model (relies on initial config)
#         logger.info("DEBUG: Getting model instance...")
#         # Use the model name you are primarily testing with
#         debug_model = get_gemini_model('gemini-2.0-flash')
#         logger.info(f"DEBUG: Got model instance: {debug_model.model_name}")

#         # 2. Prepare prompt
#         test_description = "A simple to-do list application for testing." # Keep it simple
#         debug_full_prompt = SPECIFICATION_PROMPT.format(user_description=test_description)
#         logger.info("DEBUG: Formatted prompt.")
#         # logger.debug(f"DEBUG Prompt Snippet: {debug_full_prompt[:150]}...")

#         # 3. Call generate_content
#         logger.info("DEBUG: Calling model.generate_content...")
#         # Define request options - especially timeout
#         request_options = {"timeout": 180} # 3 minutes timeout
#         debug_response = debug_model.generate_content(
#             debug_full_prompt,
#             request_options=request_options
#             # Optional: Add explicit config/safety if testing those
#             # generation_config=...,
#             # safety_settings=...
#         )
#         logger.info("DEBUG: model.generate_content call finished.")

#         # 4. Log the RAW response details extensively
#         logger.info("--- DEBUG: RAW Gemini Response Object ---")
#         try:
#              logger.info(f"DEBUG Response Candidates: {debug_response.candidates}")
#              logger.info(f"DEBUG Response Prompt Feedback: {debug_response.prompt_feedback}")
#              if hasattr(debug_response, 'text'):
#                   logger.info(f"DEBUG Response Text (first 100 chars): {debug_response.text[:100]}...")
#              else:
#                   logger.info("DEBUG Response has no direct '.text' attribute.")
#              if debug_response.candidates and hasattr(debug_response.candidates[0],'content') and debug_response.candidates[0].content.parts:
#                   logger.info(f"DEBUG Response Parts: {debug_response.candidates[0].content.parts}")
#         except Exception as log_e:
#              logger.error(f"DEBUG: Error trying to log response details: {log_e}")
#         logger.info("--- END DEBUG: RAW Gemini Response Object ---")


#         # 5. Check candidates like in the original code
#         # Check prompt_feedback first for blocking reasons
#         failure_message = None
#         response_text = None # Initialize variable to store valid text

#         try:
#             # Check 1: Did prompt feedback indicate blocking?
#             if hasattr(debug_response, 'prompt_feedback') and hasattr(debug_response.prompt_feedback, 'block_reason') and debug_response.prompt_feedback.block_reason != 0:
#                 reason = debug_response.prompt_feedback.block_reason
#                 failure_message = f"Model response blocked. Finish Reason Enum: {reason}"
#                 if hasattr(debug_response.prompt_feedback, 'safety_ratings'):
#                     logger.error(f"DEBUG Safety Ratings: {debug_response.prompt_feedback.safety_ratings}")

#             # Check 2: If not blocked, do we have candidates and parts with text?
#             elif not debug_response.candidates:
#                 failure_message = "Model response missing candidates list."
#             else:
#                 # We have candidates, check the first one
#                 candidate = debug_response.candidates[0]
#                 if not hasattr(candidate, 'content'):
#                     failure_message = "Model response candidate[0] missing 'content'."
#                 elif not candidate.content.parts: # Check if parts list is empty
#                     failure_message = "Model response candidate[0].content has no 'parts'."
#                 else:
#                     # We have parts, check the first part for text
#                     part = candidate.content.parts[0]
#                     if not hasattr(part, 'text'):
#                         failure_message = "Model response candidate[0].content.parts[0] missing 'text'."
#                     elif not part.text: # Check if text is present but empty
#                         failure_message = "Model response candidate[0].content.parts[0] has empty 'text'."
#                     else:
#                         # --- Looks like a valid text response ---
#                         response_text = part.text # Store the valid text

#             # Check 3: If we didn't get valid text, was there another finish reason?
#             if failure_message and hasattr(debug_response, 'prompt_feedback') and hasattr(debug_response.prompt_feedback, 'finish_reason'):
#                 # Add finish reason if available and different from STOP (0)
#                 f_reason = debug_response.prompt_feedback.finish_reason
#                 if f_reason != 0: # Append if it's not just STOP
#                     failure_message += f" Finish Reason Enum: {f_reason}"


#         except IndexError:
#             logger.exception("DEBUG: IndexError accessing response candidates/parts.")
#             failure_message = "Error accessing expected response structure (IndexError)."
#         except AttributeError:
#             logger.exception("DEBUG: AttributeError accessing response attributes.")
#             failure_message = "Error accessing expected response structure (AttributeError)."
#         except Exception as check_e:
#             logger.exception(f"DEBUG: Unexpected error during response validation: {check_e}")
#             failure_message = f"Unexpected error checking response: {check_e}"


#         # --- Final Outcome ---
#         if failure_message:
#             # Log and return the detected failure
#             logger.error(f"DEBUG: Call failed - {failure_message}")
#             return jsonify({"status": "error", "message": f"DEBUG CALL FAILED: {failure_message}"}), 500
#         elif response_text is None:
#             # Should not happen if logic above is correct, but safety net
#             logger.error("DEBUG: Call check completed without failure, but response_text is still None.")
#             return jsonify({"status": "error", "message": "DEBUG CALL FAILED: Unknown state, no valid text found."}), 500
#         else:
#             # --- Success Path ---
#             logger.info("DEBUG: Call successful - received valid text response.")
#             try:
#                 # Attempt parsing using the validated response_text
#                 from .models import SpecificationGenerator
#                 parser = SpecificationGenerator()
#                 parsed = parser._parse_json_response(response_text)
#                 logger.info("DEBUG: Parsing successful (first 100 chars): " + json.dumps(parsed)[:100] + "...")
#                 return jsonify({
#                     "status": "success",
#                     "message": "DEBUG CALL SUCCEEDED. Check server logs for raw response.",
#                     "parsed_snippet": json.dumps(parsed)[:200] + "..."
#                     }), 200
#             except Exception as parse_e:
#                 logger.error(f"DEBUG: Parsing failed after successful call: {parse_e}")
#                 return jsonify({
#                     "status": "error",
#                     "message": f"DEBUG CALL SUCCEEDED but parsing failed: {parse_e}",
#                     "raw_text_snippet": response_text[:200] + "..." # Return raw text snippet
#                     }), 500
#             # --- End Success Path ---

#     except Exception as e: # Catch exceptions in the main try block (model call, etc.)
#         logger.exception("--- DEBUG: UNHANDLED EXCEPTION in /debug-gemini-spec ---")
#         tb_str = traceback.format_exc()
#         logger.error(f"DEBUG Traceback:\n{tb_str}")
#         return jsonify({"status": "error", "message": f"DEBUG ROUTE EXCEPTION: {e}"}), 500
# # --- END DEBUG ROUTE ---


# --- Main execution (Not used when running with python -m) ---
if __name__ == '__main__':
    # This block is useful for direct `python server.py` testing *if* using sys.path hack
    # but won't run when using `python -m mcp_server.server`
    logger.info("Attempting to run directly (__name__ == '__main__'). This might fail with relative imports without path modification.")
    port = int(os.environ.get('MCP_PORT', 5100))
    # Set debug=True ONLY for direct script run testing if needed
    app.run(debug=True, host='127.0.0.1', port=port)