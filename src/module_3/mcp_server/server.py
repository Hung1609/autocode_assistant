from flask import Flask, request, jsonify
import logging
import os
import json
import traceback # For logging detailed errors in debug route

# Use relative imports for modules within the mcp_server package
from .execution import execute_generate_very_simple_json

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

app.route('/tools/generate_very_simple_json', methods=['POST'])
def handle_generate_very_simple_json():
    logger.info("Received request for /tools/generate_very_simple_json")
    data, error_response, status_code = get_request_data()
    if error_response:
        return error_response, status_code

    description = data.get('description')
    workspace_path = data.get('workspace_path') # From get_request_data

    if not description:
        logger.warning("Missing 'description' parameter.")
        return jsonify({"status":"error", "message":"Missing required parameter: description"}), 400

    try:
        logger.info(f"Calling execution.execute_generate_very_simple_json for: '{description[:50]}...'")
        result = execution.execute_generate_very_simple_json(workspace_path, description)

        # Determine HTTP status based on the result from execution function
        http_status = 200
        if isinstance(result, dict) and result.get("status") == "error":
            http_status = 500 # Default to 500 for server-side errors
            if "SecurityError" in result.get("message", ""): http_status = 403
            elif "Model failed" in result.get("message", ""): http_status = 502 # Bad Gateway (problem with upstream LLM)
            elif "parse model response" in result.get("message", ""): http_status = 500
        elif not isinstance(result, dict) or "status" not in result: # Unexpected result format
             logger.error(f"Unexpected result format from execute_generate_very_simple_json: {result}")
             result = {"status": "error", "message": "Internal server error: Unexpected result format from tool execution."}
             http_status = 500

        logger.info(f"Returning response for /tools/generate_very_simple_json with status {http_status}: {result}")
        return jsonify(result), http_status

    except Exception as e:
        logger.exception(f"Unhandled EXCEPTION in /tools/generate_very_simple_json handler: {e}")
        return jsonify({"status": "error", "message": f"Internal server error: {e}"}), 500

# --- Main execution (Not used when running with python -m) ---
if __name__ == '__main__':
    # This block is useful for direct `python server.py` testing *if* using sys.path hack
    # but won't run when using `python -m mcp_server.server`
    logger.info("Attempting to run directly (__name__ == '__main__'). This might fail with relative imports without path modification.")
    port = int(os.environ.get('MCP_PORT', 5100))
    # Set debug=True ONLY for direct script run testing if needed
    app.run(debug=True, host='127.0.0.1', port=port)