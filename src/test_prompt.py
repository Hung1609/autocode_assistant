import os
import sys
from config import load_environment, configure_genai
from config import get_gemini_model
from prompts import SPECIFICATION_PROMPT
import google.generativeai as genai
load_environment()
# --- 1. Lấy API Key từ biến môi trường ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Lỗi: Vui lòng đặt biến môi trường GOOGLE_API_KEY.")
    print("Ví dụ (Linux/macOS): export GOOGLE_API_KEY='YOUR_API_KEY'")
    print("Ví dụ (Windows): set GOOGLE_API_KEY=YOUR_API_KEY")
    sys.exit(1) # Thoát nếu không có key

# --- 2. Cấu hình Gemini API ---
try:
    genai.configure(api_key=api_key)
    # Chọn model - gemini-1.5-flash thường nhanh và tiết kiệm hơn cho các tác vụ này
    # Hoặc dùng 'gemini-1.5-pro-latest' nếu cần khả năng mạnh hơn
    model = get_gemini_model('gemini-2.0-flash')
    print("Đã cấu hình Gemini API thành công.")
except Exception as e:
    print(f"Lỗi cấu hình Gemini API: {e}")
    sys.exit(1)

# --- 3. Định nghĩa Prompt Template Xử lý Yêu cầu Mơ hồ ---
# (Đây là Prompt 2 từ câu trả lời trước)
prompt_template_vague = SPECIFICATION_PROMPT

# --- 4. Định nghĩa Input Mơ hồ từ Người dùng ---
vague_user_input = "create for me a flashcard web application"
# Bạn có thể thử các input khác như: "make a simple blog", "an app for notes", "a basic e-commerce site"

# --- 5. Tạo Prompt cuối cùng bằng cách chèn input người dùng ---
final_prompt = prompt_template_vague.replace("{user_description}", vague_user_input)

print("\n--- Gửi Prompt đến Gemini API ---")
print("Input gốc:", vague_user_input)
# print("\nPrompt đầy đủ gửi đi:\n", final_prompt) # Bỏ comment nếu muốn xem prompt đầy đủ

# --- 6. Gọi API Gemini ---
try:
    response = model.generate_content(final_prompt)

    # --- 7. In kết quả ---
    print("\n--- Kết quả từ Gemini (Elaborated Description) ---")
    if response.candidates:
         # Truy cập text từ candidate đầu tiên (thường là cái duy nhất trừ khi có vấn đề)
        print(response.text)
    else:
        print("API không trả về kết quả hợp lệ.")
        # In thêm thông tin nếu có lỗi safety hoặc lý do khác
        print("Response:", response)


except Exception as e:
    print(f"\nLỗi khi gọi Gemini API: {e}")
    # In thêm chi tiết lỗi nếu cần
    # print(vars(e))

print("\n--- Kết thúc Test ---")