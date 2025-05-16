from flask import Flask, request, jsonify
import execution
import logging
import os
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

def get_request_data():
    if not request.is_json:
        return None, jsonify({"status": "error", "message": "Request must be JSON"}), 400
    data = request.get_json()
    workspace_path = data.get('workspace_path')
    relative_path = data.get('path')

    if not workspace_path:
        return None, jsonify({"status": "error", "message": "Missing required parameter: workspace_path"}), 400
    return data, None, None

# API
@app.route('/tools/create_file', methods=['POST'])
def handle_create_file():
    data, error_response, status_code = get_request_data()
    if error_response:
        return error_response, status_code

    relative_path = data.get('path')
    content = data.get('content')
    workspace_path = data.get('workspace_path')

    if relative_path is None or content is None:
        return jsonify({"status": "error", "message": "Missing required parameters: path or content"}), 400

    try:
        result = execution.create_file(workspace_path, relative_path, content)
        if result["status"] == "error":
            if "Path resolution outside allowed workspace" in result.get("message","") or "Secirity Violation" in result.get("message",""):
                http_status = 403
            elif "not found" in result.get("message","").lower() or "is not a valid directory" in result.get("message",""):
                http_status = 404
            else:
                http_status = 500
            return jsonify(result), http_status
        else:
            return jsonify(result), 200
    except Exception as e:
        logging.exception("Unhandled exception in /tools/create_file")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/tools/read_file', methods=['POST'])
def handle_read_file():
    data, error_response, status_code = get_request_data()
    if error_response:
        return error_response, status_code
    
    relative_path = data.get('path')
    workspace_path = data.get('workspace_path')

    if relative_path is None:
         return jsonify({"status": "error", "message": "Missing required parameter: path"}), 400

    try:
        result = execution.read_file(workspace_path, relative_path)
        if result["status"] == "error":
             if "Path resolution outside allowed workspace" in result.get("message","") or "Security Violation" in result.get("message",""):
                  http_status = 403
             elif "not found" in result.get("message","").lower():
                  http_status = 404
             else:
                  http_status = 500
             return jsonify(result), http_status
        else:
             return jsonify(result), 200
    except Exception as e:
        logging.exception("Unhandled exception in /tools/read_file")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/tools/list_files', methods=['POST'])
def handle_list_files():
    data, error_response, status_code = get_request_data()
    if error_response:
        return error_response, status_code

    # 'path' is optional for list_files, defaults to listing the base directory
    relative_path = data.get('path', "") 
    workspace_path = data.get('workspace_path')

    try:
        result = execution.list_files(workspace_path, relative_path)
        if result["status"] == "error":
             if "Path resolution outside allowed workspace" in result.get("message","") or "Security Violation" in result.get("message",""):
                  http_status = 403
             elif "not found" in result.get("message","").lower():
                  http_status = 404
             else:
                  http_status = 500
             return jsonify(result), http_status
        else:
             return jsonify(result), 200
    except Exception as e:
        logging.exception("Unhandled exception in /tools/list_files")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/tools/create_directory', methods=['POST'])
def handle_create_directory():
    data, error_response, status_code = get_request_data()
    if error_response:
        return error_response, status_code

    relative_path = data.get('path')
    workspace_path = data.get('workspace_path')

    if relative_path is None:
         return jsonify({"status": "error", "message": "Missing required parameter: path"}), 400

    try:
        result = execution.create_directory(workspace_path, relative_path)
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
    except Exception as e:
        logging.exception("Unhandled exception in /tools/create_directory")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/tools/edit_file', methods=['POST'])
def handle_edit_file():
    data, error_response, status_code = get_request_data()
    if error_response:
        return error_response, status_code

    relative_path = data.get('path')
    changes = data.get('changes_description') 
    workspace_path = data.get('workspace_path')

    if relative_path is None or changes is None:
         return jsonify({"status": "error", "message": "Missing required parameters: path, changes_description"}), 400

    try:
        result = execution.edit_file(workspace_path, relative_path, changes)
        if result["status"] == "error":
             if "Path resolution outside allowed workspace" in result.get("message","") or "Security Violation" in result.get("message",""):
                  http_status = 403
             elif "not found" in result.get("message","").lower():
                  http_status = 404
             else:
                  http_status = 500
             return jsonify(result), http_status
        else:
             return jsonify(result), 200
    except Exception as e:
        logging.exception("Unhandled exception in /tools/edit_file")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('MCP_PORT', 5100))
    # For development, debug=True.
    # For anything else, set debug=False. Debug mode has security implications.
    app.run(debug=False, host='127.0.0.1', port=port)