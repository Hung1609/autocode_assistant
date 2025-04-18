# import os
# import sys
# from config import load_environment, configure_genai
# from config import get_gemini_model
# from prompts import DESIGN_PROMPT
# from outputs import schedule_web_app_20250416.json
# import google.generativeai as genai
# load_environment()
# # --- 1. Lấy API Key từ biến môi trường ---
# api_key = os.getenv("GEMINI_API_KEY")
# if not api_key:
#     print("Lỗi: Vui lòng đặt biến môi trường GOOGLE_API_KEY.")
#     sys.exit(1) # Thoát nếu không có key

# # --- 2. Cấu hình Gemini API ---
# try:
#     genai.configure(api_key=api_key)
#     model = get_gemini_model('gemini-2.0-flash')
#     print("Đã cấu hình Gemini API thành công.")
# except Exception as e:
#     print(f"Lỗi cấu hình Gemini API: {e}")
#     sys.exit(1)

# # --- 3. Định nghĩa Prompt Template Xử lý Yêu cầu Mơ hồ ---
# # (Đây là Prompt 2 từ câu trả lời trước)
# prompt_template_vague = SPECIFICATION_PROMPT

# # --- 4. Định nghĩa Input Mơ hồ từ Người dùng ---
# vague_user_input = "create for me a flashcard web application"
# # Bạn có thể thử các input khác như: "make a simple blog", "an app for notes", "a basic e-commerce site"

# # --- 5. Tạo Prompt cuối cùng bằng cách chèn input người dùng ---
# final_prompt = prompt_template_vague.replace("{user_description}", vague_user_input)

# print("\n--- Gửi Prompt đến Gemini API ---")
# print("Input gốc:", vague_user_input)
# # print("\nPrompt đầy đủ gửi đi:\n", final_prompt) # Bỏ comment nếu muốn xem prompt đầy đủ

# # --- 6. Gọi API Gemini ---
# try:
#     response = model.generate_content(final_prompt)

#     # --- 7. In kết quả ---
#     print("\n--- Kết quả từ Gemini (Elaborated Description) ---")
#     if response.candidates:
#          # Truy cập text từ candidate đầu tiên (thường là cái duy nhất trừ khi có vấn đề)
#         print(response.text)
#     else:
#         print("API không trả về kết quả hợp lệ.")
#         # In thêm thông tin nếu có lỗi safety hoặc lý do khác
#         print("Response:", response)


# except Exception as e:
#     print(f"\nLỗi khi gọi Gemini API: {e}")
#     # In thêm chi tiết lỗi nếu cần
#     # print(vars(e))

# print("\n--- Kết thúc Test ---")


import os
import sys
import json # Thêm thư viện json để xử lý output
import google.generativeai as genai

# --- 0. Import các thành phần tùy chỉnh ---
# Đảm bảo đường dẫn import phù hợp với cấu trúc dự án của bạn
try:
    # Giả sử script này nằm trong thư mục src/
    # Nếu script nằm ở root, bạn có thể cần điều chỉnh sys.path hoặc cách import
    # from config import load_environment, get_gemini_model # Cách này nếu config.py cùng cấp
    # from prompts import DESIGN_PROMPT                 # Cách này nếu prompts.py cùng cấp

    # Cách import nếu chạy từ project root và src là một package (có __init__.py)
    # Hoặc nếu thêm src vào sys.path
    from config import load_environment, get_gemini_model
    from prompts import DESIGN_PROMPT # Sử dụng prompt của Agent 2
except ImportError as e:
    print(f"Lỗi import: {e}. Hãy đảm bảo cấu trúc thư mục và PYTHONPATH đúng.")
    print("Kiểm tra xem bạn có đang chạy script từ thư mục gốc của dự án không?")
    # Thử thêm thư mục gốc vào sys.path nếu cần
    # project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # if project_root not in sys.path:
    #     sys.path.insert(0, project_root)
    # try:
    #     from src.config import load_environment, get_gemini_model
    #     from src.prompts import DESIGN_PROMPT
    # except ImportError:
    #     print("Vẫn không thể import. Vui lòng kiểm tra lại.")
    #     sys.exit(1)
    sys.exit(1)


# --- 1. Tải biến môi trường và lấy API Key ---
try:
    load_environment() # Gọi hàm load từ config (nếu bạn dùng python-dotenv)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Lỗi: Vui lòng đặt biến môi trường GEMINI_API_KEY.")
        sys.exit(1) # Thoát nếu không có key
except Exception as e:
    print(f"Lỗi khi tải môi trường hoặc lấy API key: {e}")
    sys.exit(1)

# --- 2. Cấu hình Gemini API ---
try:
    genai.configure(api_key=api_key)
    # Lưu ý: Model 'gemini-2.0-flash' có thể không tồn tại.
    # Sử dụng 'gemini-1.5-flash-latest' hoặc 'gemini-1.5-pro-latest'.
    model_name = 'gemini-2.0-flash' # Ưu tiên flash cho tốc độ/chi phí
    model = get_gemini_model(model_name)
    print(f"Đã cấu hình Gemini API thành công với model: {model_name}")
except Exception as e:
    print(f"Lỗi cấu hình Gemini API: {e}")
    sys.exit(1)

# --- 3. Đọc Input JSON từ file ---
input_json_filename = "schedule_web_app_20250416.json"
# Đường dẫn tương đối từ vị trí chạy script đến thư mục outputs
# Nếu chạy script từ project root:
input_json_path = os.path.join("outputs", input_json_filename)
# Nếu chạy script từ thư mục src/:
# input_json_path = os.path.join("..", "outputs", input_json_filename)

agent1_output_json_str = None
try:
    with open(input_json_path, 'r', encoding='utf-8') as f:
        agent1_output_json_str = f.read()
    print(f"Đã đọc thành công file input: {input_json_path}")
    # Optional: Validate if the input is valid JSON before sending
    try:
        json.loads(agent1_output_json_str)
        print("Input JSON từ file hợp lệ.")
    except json.JSONDecodeError as e:
        print(f"Cảnh báo: Nội dung file input {input_json_path} không phải là JSON hợp lệ: {e}")
        # Quyết định có nên tiếp tục hay không tùy thuộc vào yêu cầu
        # sys.exit(1) # Uncomment để thoát nếu input bắt buộc phải là JSON hợp lệ

except FileNotFoundError:
    print(f"Lỗi: Không tìm thấy file input tại đường dẫn: {input_json_path}")
    print(f"   Thư mục làm việc hiện tại: {os.getcwd()}")
    sys.exit(1)
except Exception as e:
    print(f"Lỗi khi đọc file input: {e}")
    sys.exit(1)

# --- 4. Sử dụng Prompt Template của Agent 2 ---
prompt_template_agent2 = DESIGN_PROMPT

# --- 5. Tạo Prompt cuối cùng bằng cách chèn input JSON từ file ---
final_prompt = prompt_template_agent2.replace("{agent1_output_json}", agent1_output_json_str)

print("\n--- Gửi Prompt đến Gemini API ---")
# print("\nPrompt đầy đủ gửi đi:\n", final_prompt[:1000] + "...") # In 1000 ký tự đầu để kiểm tra

# --- 6. Gọi API Gemini ---
try:
    # Cân nhắc tăng thời gian chờ hoặc xử lý lỗi nếu prompt quá dài/phức tạp
    # generation_config = genai.types.GenerationConfig(temperature=0.5) # Ví dụ
    response = model.generate_content(final_prompt) #, generation_config=generation_config)

    # --- 7. Xử lý và In kết quả ---
    print("\n--- Kết quả từ Gemini (System Design Specification) ---")
    if response.candidates:
        result_text = response.text
        print("--- Phản hồi thô từ LLM ---")
        print(result_text)
        print("--------------------------\n")

        # --- 8. Kiểm tra định dạng JSON của Output ---
        print("--- Kiểm tra định dạng JSON của Output ---")
        try:
            # Cố gắng loại bỏ ```json và ``` nếu có
            processed_text = result_text.strip()
            if processed_text.startswith("```json"):
                processed_text = processed_text[7:]
            if processed_text.endswith("```"):
                processed_text = processed_text[:-3]
            processed_text = processed_text.strip() # Xóa khoảng trắng thừa sau khi cắt

            # Thử parse output thành JSON
            parsed_json = json.loads(processed_text)
            print("✅ Output là một JSON hợp lệ.")
            # Optional: In lại JSON đã được định dạng đẹp
            # print("\n--- Output JSON đã định dạng ---")
            # print(json.dumps(parsed_json, indent=2, ensure_ascii=False)) # ensure_ascii=False cho tiếng Việt
            # print("--------------------------\n")

        except json.JSONDecodeError as e:
            print(f"❌ Lỗi: Output không phải là JSON hợp lệ. Lỗi tại vị trí {e.pos}: {e.msg}")
            print("   Lưu ý: Model có thể đã thêm văn bản giới thiệu/kết luận hoặc markdown.")
            print("   Phần text đã cố gắng parse (500 chars):\n---\n", processed_text[:500], "\n---")
        except Exception as e:
            print(f"❌ Lỗi không xác định khi xử lý output JSON: {e}")

    else:
        print("API không trả về kết quả hợp lệ.")
        # In thêm thông tin nếu có lỗi safety hoặc lý do khác
        print("Response:", response)
        try:
             print("Prompt Feedback:", response.prompt_feedback)
        except Exception:
             pass # Bỏ qua nếu không có prompt_feedback


except Exception as e:
    print(f"\nLỗi khi gọi Gemini API hoặc xử lý kết quả: {e}")
    # In thêm chi tiết lỗi nếu cần
    import traceback
    traceback.print_exc()

print("\n--- Kết thúc Test ---")