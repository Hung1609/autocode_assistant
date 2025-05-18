# This module is responsible for creating API endpoints for agent_core.py (client) to call and implement defined tools.

from flask import Flask, request, jsonify, g
import execution
import logging
import os
import uuid
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(g, 'request_id', 'N/A')
        return True

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(request_id)s] - %(message)s')
handler.setFormatter(formatter)

root_logger = logging.getLogger()
if root_logger.hasHandlers():
    root_logger.handlers.clear()
root_logger.addHandler(handler) 
root_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())

app = Flask(__name__)

@app.before_request
def assign_request_id():
    g.request_id = str(uuid.uuid4())

def get_base_request_data(): # Validates if the request is JSON and extracts the JSON data and workspace_path.
    if not request.is_json:
        logger.warning(f"Request is not JSON. Request headers: {request.headers}")
        return None, None, jsonify({"status": "error", "message": "Request must be JSON"}), 400
    data = request.get_json()
    if data is None:
        logger.warning("Failed to parse JSON data from request.")
        return None, None, jsonify({"status": "error", "message": "Invalid JSON data provided"}), 400
    workspace_path = data.get('workspace_path')
    if not workspace_path:
        logger.warning("workspace_path missing from request payload.")
        return data, None, jsonify({"status": "error", "message": "Missing required parameter: workspace_path"}), 400
    if not isinstance(workspace_path, str) or not os.path.isabs(workspace_path):
        logger.warning(f"Invalid workspace_path received: '{workspace_path}'. Must be an absolute path string.")
        # return data, None, jsonify({"status": "error", "message": "Invalid workspace_path. Must be an absolute path."}), 400
        pass
    return data, workspace_path, None, None

@app.route('/status', methods=['GET'])
@app.route('/health', methods=['GET'])
def health_check():
    logger.info("Health check endpoint called.")
    return jsonify({"status": "ok", "message": "MCP Server is running"}), 200

# API
@app.route('/tools/create_file', methods=['POST'])
def handle_create_file():
    data, workspace_path, error_response, status_code = get_base_request_data()
    if error_response:
        return error_response, status_code

    relative_path = data.get('path')
    content = data.get('content')

    if relative_path is None or content is None:
        logger.warning("create_file: Missing path or content.")
        return jsonify({"status": "error", "message": "Missing required parameters: path or content"}), 400

    try:
        logger.info(f"Calling execution.create_file for workspace: '{workspace_path}', path: '{relative_path}'")
        result = execution.create_file(workspace_path, relative_path, content)
        if result["status"] == "error":
            if "Path resolution outside allowed workspace" in result.get("message","") or "Security Violation" in result.get("message",""):
                http_status = 403
            elif "not found" in result.get("message","").lower() or "is not a valid directory" in result.get("message",""):
                http_status = 404
            else:
                http_status = 500
            logger.warning(f"create_file failed for '{relative_path}': {result.get('message','')}")
            return jsonify(result), http_status
        else:
            logger.info(f"create_file successful for '{relative_path}'.")
            return jsonify(result), 200
    except Exception as e:
        logger.exception("Unhandled exception in /tools/create_file")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/tools/read_file', methods=['POST'])
def handle_read_file():
    data, workspace_path, error_response, status_code = get_base_request_data()
    if error_response:
        return error_response, status_code
    
    relative_path = data.get('path')

    if relative_path is None:
         logger.warning("read_file: Missing path.")
         return jsonify({"status": "error", "message": "Missing required parameter: path"}), 400

    try:
        logger.info(f"Calling execution.read_file for workspace: '{workspace_path}', path: '{relative_path}'")
        result = execution.read_file(workspace_path, relative_path)
        if result["status"] == "error":
             if "Path resolution outside allowed workspace" in result.get("message","") or "Security Violation" in result.get("message",""):
                  http_status = 403
             elif "not found" in result.get("message","").lower():
                  http_status = 404
             else:
                  http_status = 500
             logger.warning(f"read_file failed for '{relative_path}': {result.get('message','')}")
             return jsonify(result), http_status
        else:
             logger.info(f"read_file successful for '{relative_path}'.")
             return jsonify(result), 200
    except Exception as e:
        logger.exception("Unhandled exception in /tools/read_file")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/tools/list_files', methods=['POST'])
def handle_list_files():
    data, workspace_path, error_response, status_code = get_base_request_data()
    if error_response:
        return error_response, status_code

    relative_path = data.get('path', "") 

    try:
        logger.info(f"Calling execution.list_files for workspace: '{workspace_path}', path: '{relative_path or '<root>'}'")
        result = execution.list_files(workspace_path, relative_path)
        if result["status"] == "error":
             # ... (logic ánh xạ lỗi giữ nguyên) ...
             if "Path resolution outside allowed workspace" in result.get("message","") or "Security Violation" in result.get("message",""):
                  http_status = 403
             elif "not found" in result.get("message","").lower():
                  http_status = 404
             else:
                  http_status = 500
             logger.warning(f"list_files failed for '{relative_path}': {result.get('message','')}")
             return jsonify(result), http_status
        else:
             logger.info(f"list_files successful for '{relative_path or '<root>'}'. Items: {len(result.get('items',[]))}")
             return jsonify(result), 200
    except Exception as e:
        logger.exception("Unhandled exception in /tools/list_files")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/tools/create_directory', methods=['POST'])
def handle_create_directory():
    data, workspace_path, error_response, status_code = get_base_request_data()
    if error_response:
        return error_response, status_code

    relative_path = data.get('path')

    if relative_path is None:
         logger.warning("create_directory: Missing path.")
         return jsonify({"status": "error", "message": "Missing required parameter: path"}), 400

    try:
        logger.info(f"Calling execution.create_directory for workspace: '{workspace_path}', path: '{relative_path}'")
        result = execution.create_directory(workspace_path, relative_path)
        if result["status"] == "error":
             # ... (logic ánh xạ lỗi giữ nguyên) ...
             if "Path resolution outside allowed workspace" in result.get("message","") or "Security Violation" in result.get("message",""):
                  http_status = 403
             elif "not found" in result.get("message","").lower() or "is not a valid directory" in result.get("message",""):
                  http_status = 404
             else:
                  http_status = 500
             logger.warning(f"create_directory failed for '{relative_path}': {result.get('message','')}")
             return jsonify(result), http_status
        else:
             logger.info(f"create_directory successful for '{relative_path}'.")
             return jsonify(result), 200
    except Exception as e:
        logger.exception("Unhandled exception in /tools/create_directory")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/tools/edit_file', methods=['POST'])
def handle_edit_file():
    data, workspace_path, error_response, status_code = get_base_request_data()
    if error_response:
        return error_response, status_code

    relative_path = data.get('path')
    changes = data.get('changes_description')

    if relative_path is None or changes is None:
         return jsonify({"status": "error", "message": "Missing required parameters: path, changes_description"}), 400

    if relative_path is None or changes is None:
         logger.warning("edit_file: Missing path or changes_description.")
         return jsonify({"status": "error", "message": "Missing required parameters: path, changes_description"}), 400

    try:
        logger.info(f"Calling execution.edit_file for workspace: '{workspace_path}', path: '{relative_path}'")
        result = execution.edit_file(workspace_path, relative_path, changes)
        if result["status"] == "error":
             # ... (logic ánh xạ lỗi giữ nguyên) ...
             if "Path resolution outside allowed workspace" in result.get("message","") or "Security Violation" in result.get("message",""):
                  http_status = 403
             elif "not found" in result.get("message","").lower():
                  http_status = 404
             else:
                  http_status = 500
             logger.warning(f"edit_file failed for '{relative_path}': {result.get('message','')}")
             return jsonify(result), http_status
        else:
             logger.info(f"edit_file successful for '{relative_path}'.")
             return jsonify(result), 200
    except Exception as e:
        logger.exception("Unhandled exception in /tools/edit_file")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('MCP_PORT', 5100))
    # debug=False là tốt cho production.
    # Khi phát triển, bạn có thể đặt debug=True nhưng hãy cẩn thận.
    logger.info(f"MCP Server starting on host 127.0.0.1 port {port}")
    app.run(debug=False, host='127.0.0.1', port=port)