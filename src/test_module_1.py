import streamlit as st
import json
import os
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def configure_genai():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.error("GEMINI_API_KEY not found in environment variables")
            return False
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"Error configuring Gemini API: {str(e)}")
        return False

def get_timestamp_filename(project_name=None, extension="json"):
    if project_name:
        clean_name = "".join(c if c.isalnum() else "_" for c in project_name).lower()
    else:
        clean_name = "specification"
    timestamp = datetime.now().strftime("%Y%m%d")
    return f"{clean_name}_{timestamp}.{extension}"

def save_to_json(data, filename=None):
    if filename is None:
        project_name = data.get("project_name", "unnamed_project")
        filename = get_timestamp_filename(project_name=project_name)
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
    filepath = os.path.join("outputs", filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath

def agent_clarify(history):
    # history: list of dicts with keys: role, content
    model = genai.GenerativeModel('gemini-2.0-flash')
    messages = []
    for turn in history:
        if turn["role"] == "user":
            messages.append({"role": "user", "parts": [turn["content"]]})
        else:
            messages.append({"role": "model", "parts": [turn["content"]]})
    response = model.generate_content(messages)
    return response.text

def main():
    st.set_page_config(page_title="Module 1 - Software Requirements Specification Generator", layout="wide")
    if not configure_genai():
        st.error("Failed to configure Gemini API. Please check your API key.")
        return

    st.title("Module 1 - Software Requirements Clarification & Specification Generator")
    st.markdown("This tool helps you clarify your requirements with an AI agent before generating the final specification.")

    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        st.markdown("---")
        st.markdown("This module is using Gemini API to process.")

    # Chat-based clarification
    if "clarify_history" not in st.session_state:
        st.session_state.clarify_history = []
    if "clarify_done" not in st.session_state:
        st.session_state.clarify_done = False

    st.subheader("Requirements Clarification Chat")
    for turn in st.session_state.clarify_history:
        if turn["role"] == "user":
            st.chat_message("user").write(turn["content"])
        else:
            st.chat_message("assistant").write(turn["content"])

    if not st.session_state.clarify_done:
        user_input = st.chat_input("Enter your software requirements or answer agent's questions...")
        if user_input:
            st.session_state.clarify_history.append({"role": "user", "content": user_input})
            with st.spinner("Agent is thinking..."):
                agent_reply = agent_clarify(st.session_state.clarify_history)
            st.session_state.clarify_history.append({"role": "assistant", "content": agent_reply})

            # Nếu agent xác nhận đã đủ thông tin, cho phép sinh đặc tả
            if "no further questions" in agent_reply.lower() or "ready to generate" in agent_reply.lower():
                st.session_state.clarify_done = True
                st.success("Clarification complete! You can now generate the specification.")

    if st.session_state.clarify_done:
        if st.button("Generate Specification", use_container_width=True):
            with st.spinner("Generating technical specification..."):
                # Lấy toàn bộ hội thoại làm đầu vào cho prompt
                conversation = "\n".join(
                    [f"{turn['role'].capitalize()}: {turn['content']}" for turn in st.session_state.clarify_history]
                )
                prompt = (
                    "Based on the following clarified requirements conversation, generate a structured software specification in JSON format. "
                    "Do NOT include data_entities. Output only JSON.\n\n"
                    f"{conversation}"
                )
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content(prompt)
                try:
                    response_text = response.text
                    if "```json" in response_text:
                        json_text = response_text.split("```json")[1].split("```")[0].strip()
                        spec_data = json.loads(json_text)
                    else:
                        spec_data = json.loads(response_text)
                    # Đảm bảo không có data_entities
                    spec_data.pop("data_entities", None)
                    # Lưu file
                    filepath = save_to_json(spec_data)
                    st.session_state.spec_data = spec_data
                    st.session_state.filepath = filepath
                    st.success(f"Specification generated and saved to {filepath}")
                except Exception as e:
                    st.error(f"Error parsing or saving specification: {str(e)}")

    # Hiển thị kết quả và nút download
    if "spec_data" in st.session_state:
        st.markdown("---")
        st.subheader("Generated Specification")
        st.json(st.session_state.spec_data)
        json_str = json.dumps(st.session_state.spec_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="💾 Download JSON",
            data=json_str,
            file_name=st.session_state.filepath.split(os.sep)[-1],
            mime="application/json",
            use_container_width=True
        )

if __name__ == "__main__":
    main()