import json
import google.generativeai as genai
import os
import subprocess


def parse_json_and_generate_scaffold_plan(json_data):
    

# import os
# from dotenv import load_dotenv
# import logging
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain.agents import AgentExecutor, create_react_agent
# from langchain import hub

# from tools import all_tools

# logging_dir = os.path.join(os.path.dirname(__file__), 'logs')
# os.makedirs(logging_dir, exist_ok=True)

# logging_file_path = os.path.join(logging_dir, 'agent.log')
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler(logging_file_path), # Log to file
#         logging.StreamHandler() # Log to console as well
#     ])

# dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
# load_dotenv(dotenv_path=dotenv_path)
# logging.info("Load env from: %s", dotenv_path)

# gemini_api_key = os.getenv("GEMINI_API_KEY")

# if not gemini_api_key:
#     logging.error("GEMINI_API_KEY not found in .env file.")
#     exit()
# else:
#     logging.info("GEMINI_API_KEY loaded successfully.")

# try:
#     llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro-exp-03-25", google_api_key=gemini_api_key)
#     logging.info("LLM initialized successfully.")

# except Exception as e:
#     logging.exception("Failed to initialize LLM: %s", e)
#     exit()

# # Pull a standard ReAct agent prompt
# prompt = hub.pull("hwchase17/react")

# agent = create_react_agent(llm, all_tools, prompt)
# logging.info("Agent created successfully.")

# # Agent Executor responsible for running the agent loop LLM -> decide action -> run tool -> get observation -> LLM
# agent_executor = AgentExecutor(
#     agent=agent,
#     tools=all_tools,
#     verbose=True,  # Set to True to see process
#     handle_parsing_errors=True,  # Handle parsing errors gracefully
#     max_iterations=4,
# )
# logging.info("Agent executor created successfully.")

# while True:
#     try:
#         user_input = input("You: ")
#         if user_input.lower() == 'exit':
#             logging.info("Exiting interaction loop.")
#             break
        
#         logging.info((f"Received user input: {user_input}"))

#         response = agent_executor.invoke({"input": user_input})
#         agent_response = response.get('output','Agent did not produce a final output.')

#         logging.info(f"Agent final response: {agent_response}")
#         print(f"Agent: {agent_response}") # Display final answer to user

#     except Exception as e:
#         logging.exception(f"An error occurred during agent execution: {e}")
#         print("Agent: Sorry, an error occurred. Please check the logs.")

# logging.info("Agent script finished.")