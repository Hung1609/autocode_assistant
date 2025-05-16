# file định dạng các tools: create_file, read_file, list_files, create_directory, edit_file

import os
from pathlib import Path
import logging
import json
from .utils import (_resolve_and_validate_path, SecurityError)
from .utils import save_data_to_json_file # Needs refactored save util
import google.generativeai as genai


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
API_KEY="AIzaSyBupmYhVsG_o12_LoGFlYSfaZT3eN0bVR0"
MODEL_NAME = "gemini-2.0-flash"

# Tool tạo file
def create_file(base_dir_str, relative_path_str, content):
    logging.info(f"Attempting to create file '{relative_path_str}' in base directory '{base_dir_str}'")
    try:
        target_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        target_path.parent.mkdir(parents=True, exist_ok=True) # tạo các thư mục cha nếu chưa tồn tại
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logging.info(f"File created successfully at {target_path}")
        return {"status": "success", "message": f"File '{relative_path_str}' created successfully."}

    except (ValueError, SecurityError) as e: # Lỗi liên quan đến bảo mật
        logging.error(f"Error creating file '{relative_path_str}': {e}")
        return {"status": "error", "message": str(e)}
    except OSError as e: # Lỗi liên quan đến OS
        logging.error(f"OS Error creating file '{relative_path_str}': {e}")
        return {"status": "error", "message": f"Could not create file '{relative_path_str}': {e}"}
    except Exception as e: #  Các lỗi khác
        logging.exception(f"Unexpected error creating file '{relative_path_str}': {e}")
        return {"status": "error", "message": "An unexpected server error occurred."}

# Tool đọc file
def read_file(base_dir_str, relative_path_str):
    logging.info(f"Attempting to read file '{relative_path_str}' in base '{base_dir_str}'")
    try:
        target_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        if not target_path.is_file():
            logging.warning(f"File not found for reading: {target_path}")
            return {"status": "error", "message": f"File not found: '{relative_path_str}'"}

        content = target_path.read_text(encoding='utf-8')
        logging.info(f"File read successfully: {target_path}")
        return {"status": "success", "content": content}

    except (ValueError, SecurityError) as e:
        logging.error(f"Error reading file '{relative_path_str}': {e}")
        return {"status": "error", "message": str(e)}
    except OSError as e:
        logging.error(f"OS Error reading file '{relative_path_str}': {e}")
        return {"status": "error", "message": f"Could not read file '{relative_path_str}': {e}"}
    except Exception as e:
        logging.exception(f"Unexpected error reading file '{relative_path_str}': {e}")
        return {"status": "error", "message": "An unexpected server error occurred."}

# Tool liệt kê các file
def list_files(base_dir_str, relative_path_str=""):
    logging.info(f"Attempting to list files in '{relative_path_str or '.'}' within base '{base_dir_str}'")
    try:
        target_dir_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        if not target_dir_path.is_dir():
            logging.warning(f"Directory not found for listing: {target_dir_path}")
            return {"status": "error", "message": f"Directory not found: '{relative_path_str}'"}

        items = []
        for item in target_dir_path.iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file"
            })
        logging.info(f"Successfully listed directory contents: {target_dir_path}")
        return {"status": "success", "items": items}

    except (ValueError, SecurityError) as e:
        logging.error(f"Validation/Security Error listing files in '{relative_path_str}': {e}")
        return {"status": "error", "message": str(e)}
    except OSError as e:
        logging.error(f"OS Error listing files in '{relative_path_str}': {e}")
        return {"status": "error", "message": f"Could not list directory '{relative_path_str}': {e}"}
    except Exception as e:
        logging.exception(f"Unexpected error listing files in '{relative_path_str}': {e}")
        return {"status": "error", "message": "An unexpected server error occurred."}

# Tool tạo đường dẫn thư mục
def create_directory(base_dir_str, relative_path_str):
    logging.info(f"Attempting to create directory '{relative_path_str}' in base '{base_dir_str}'")
    if not relative_path_str: 
         return {"status": "error", "message": "Directory path cannot be empty."}
    try:
        target_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        target_path.mkdir(parents=True, exist_ok=True)

        logging.info(f"Successfully ensured directory exists: {target_path}")
        return {"status": "success", "message": f"Directory '{relative_path_str}' created or already exists."}

    except (ValueError, SecurityError) as e:
        logging.error(f"Validation/Security Error creating directory '{relative_path_str}': {e}")
        return {"status": "error", "message": str(e)}
    except OSError as e:
        logging.error(f"OS Error creating directory '{relative_path_str}': {e}")
        return {"status": "error", "message": f"Could not create directory '{relative_path_str}': {e}"}
    except Exception as e:
        logging.exception(f"Unexpected error creating directory '{relative_path_str}': {e}")
        return {"status": "error", "message": "An unexpected server error occurred."}

# Tool chỉnh sửa file (tạm thời không cần)
def edit_file(base_dir_str, relative_path_str, changes_description):
    logging.info(f"Attempting to edit file '{relative_path_str}' in base '{base_dir_str}' with changes: '{changes_description[:50]}...'")
    try:
        target_path = _resolve_and_validate_path(base_dir_str, relative_path_str)
        if not target_path.is_file():
            logging.warning(f"File not found for editing: {target_path}")
            return {"status": "error", "message": f"File not found: '{relative_path_str}'"}

        # Đổi toàn bộ content cũ bằng content mới chứ không phải sửa đổi(cần chỉnh sửa thêm)
        new_content = changes_description
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        logging.info(f"Successfully edited (overwritten) file: {target_path}")
        return {"status": "success", "message": f"File '{relative_path_str}' edited successfully."}

    except (ValueError, SecurityError) as e:
        logging.error(f"Validation/Security Error editing file '{relative_path_str}': {e}")
        return {"status": "error", "message": str(e)}
    except OSError as e:
        logging.error(f"OS Error editing file '{relative_path_str}': {e}")
        return {"status": "error", "message": f"Could not edit file '{relative_path_str}': {e}"}
    except Exception as e:
        logging.exception(f"Unexpected error editing file '{relative_path_str}': {e}")
        return {"status": "error", "message": "An unexpected server error occurred."}
    
def execute_generate_very_simple_json(base_dir_str, description):
    logger.info(f"[EXECUTION-SIMPLE] Generating simple JSON for: '{description[:50]}...'")
    try:
        # VERY Simple Prompt
        SYSTEM_INSTRUCTION = f"""Based on the following user description, provide a short summary and list up to 5 main keywords.
        User Description: "{description}"
        Output ONLY a valid JSON object with two keys: "summary" (a string) and "keywords" (a list of strings).
        Example:
        {{
        "summary": "A brief summary of the description.",
        "keywords": ["keyword1", "keyword2", "keyword3"]
        }}
        """
        genai.configure(api_key=API_KEY)
        
        model = genai.GenerativeModel(
            MODEL_NAME
        )
        request_options = {"timeout": 60} # Shorter timeout for simple task
        logger.info("[EXECUTION-SIMPLE] Calling model.generate_content...")
        response = model.generate_content(
            SYSTEM_INSTRUCTION,
            request_options=request_options
        )
        logger.info("[EXECUTION-SIMPLE] Received response from model.")

        # 4. Robust check for response validity (copied & adapted from debug route)
        failure_message = None
        response_text_content = None # To store the actual text
        finish_reason_val = None

        if hasattr(response, 'prompt_feedback') and hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason != 0:
            finish_reason_val = response.prompt_feedback.block_reason
            failure_message = f"Model response blocked. Finish Reason Enum: {finish_reason_val}"
            if hasattr(response.prompt_feedback, 'safety_ratings'):
                logger.error(f"Safety Ratings: {response.prompt_feedback.safety_ratings}")
        elif not response.candidates:
            failure_message = "Model response missing candidates list."
        else:
            candidate = response.candidates[0] # Assuming at least one candidate
            if not hasattr(candidate, 'content'):
                failure_message = "Model response candidate[0] missing 'content'."
            elif not candidate.content.parts: # Check if parts list is empty
                failure_message = "Model response candidate[0].content has no 'parts'."
            else:
                part = candidate.content.parts[0] # Assuming at least one part
                if not hasattr(part, 'text') or not part.text: # Check if text is missing or empty
                    failure_message = "Model response candidate[0].content.parts[0] has missing or empty 'text'."
                else:
                    response_text_content = part.text # Success - got text

        if failure_message and hasattr(response, 'prompt_feedback') and hasattr(response.prompt_feedback, 'finish_reason'):
              f_reason = response.prompt_feedback.finish_reason
              if f_reason != 0: failure_message += f" Finish Reason Enum: {f_reason}"


        # 5. Handle outcome
        if failure_message:
            logger.error(f"[EXECUTION-SIMPLE] Model call failed: {failure_message}")
            return {"status": "error", "message": f"Model did not generate valid content: {failure_message}"}
        elif response_text_content is None:
             logger.error("[EXECUTION-SIMPLE] Failed: No failure detected by checks, but response_text_content is still None.")
             return {"status": "error", "message": "Model generation failed for an unknown reason (no text returned)."}
        else:
             logger.info("[EXECUTION-SIMPLE] Model call successful, attempting to parse and save...")
             # Parse the response text
             try:
                 # Clean potential markdown ```json ... ```
                 clean_text = response_text_content.strip()
                 if clean_text.startswith("```json"):
                     clean_text = clean_text[7:]
                 if clean_text.endswith("```"):
                     clean_text = clean_text[:-3]
                 clean_text = clean_text.strip()

                 output_data = json.loads(clean_text)
                 if not isinstance(output_data, dict):
                     raise ValueError("Parsed data is not a dictionary.")
                 logger.info("[EXECUTION-SIMPLE] Parsing successful.")
             except Exception as parse_e:
                 logger.error(f"[EXECUTION-SIMPLE] Failed to parse model response: {parse_e}. Raw text: '{response_text_content[:200]}...'")
                 return {"status": "error", "message": f"Failed to parse model's JSON response: {parse_e}"}

             # Save the generated data to a fixed file name for this test
             relative_filename = "simple_output.json"
             # Using the save_data_to_json_file from utils.py
             save_result = save_data_to_json_file(output_data, base_dir_str, relative_filename)

             if isinstance(save_result, dict) and save_result.get("status") == "error":
                 logger.error(f"[EXECUTION-SIMPLE] Failed to save simple_output.json: {save_result.get('message')}")
                 return save_result # Propagate save error
             elif isinstance(save_result, str): # save_result is the full path
                 logger.info(f"[EXECUTION-SIMPLE] Simple JSON generated and saved to: {relative_filename}")
                 return {"status": "success", "message": f"Simple JSON generated and saved to {relative_filename}.", "filepath": relative_filename}
             else:
                 logger.error(f"[EXECUTION-SIMPLE] Unexpected result from save_data_to_json_file: {save_result}")
                 return {"status": "error", "message": "File saving failed after simple JSON generation due to internal error."}

    except ValueError as ve: # Catch ValueErrors raised by get_gemini_model (e.g. API key)
        logger.exception(f"[EXECUTION-SIMPLE] Configuration or input error: {ve}")
        return {"status": "error", "message": f"Configuration error: {ve}"}
    except Exception as e:
        logger.exception(f"[EXECUTION-SIMPLE] Unexpected error: {e}")
        return {"status": "error", "message": f"An unexpected server error occurred: {e}"}