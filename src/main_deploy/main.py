from specification_agent import SpecificationAgent
from design_agent import DesignAgent
from autogen import UserProxyAgent, GroupChat, GroupChatManager

# Initialize your core agent classes
spec_agent_instance = SpecificationAgent()
design_agent_instance = DesignAgent()

# Create AutoGen ConversableAgent wrappers
autogen_spec_agent = spec_agent_instance.to_autogen_agent()
autogen_design_agent = design_agent_instance.to_autogen_agent()

# Create a UserProxyAgent that acts as the initiator and can call functions
# It needs to know about ALL functions it might want to call
orchestrator_proxy = UserProxyAgent(
    name="Orchestrator",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: "TERMINATE" in x.get("content", "").upper(),
    code_execution_config={"work_dir": "temp_scripts"}, # for calling python scripts if needed
    function_map={
        "generate_specification": autogen_spec_agent.generate_specification,
        "generate_design": autogen_design_agent.generate_design
        # Add functions for CodingAgent, TestingAgent etc. later
    }
)

# --- Sequential Flow using function calls ---

# Step 1: Generate Specification
user_prompt = "I need a simple task management web app with user login, tasks with name/due date, and filter by status."
print("Orchestrator: Initiating Specification Generation...")

# The orchestrator_proxy will "talk" to the autogen_spec_agent
# and suggest calling the 'generate_specification' function.
# This requires careful prompting of the orchestrator_proxy OR
# a direct call from the script (which might be simpler for the initial sequential steps).

# A more direct, less "chatty" way for the first two sequential steps:
try:
    print(f"\n--- Running Specification Agent ---")
    spec_data = spec_agent_instance.generate_specification(user_prompt) # Directly call the method
    print(f"Specification Generated. Project: {spec_data['project_Overview']['project_Name']}")
    # You could then convert this spec_data to a message for the next agent
    # e.g., print(f"Here is the specification:\n{json.dumps(spec_data, indent=2)}")

    print(f"\n--- Running Design Agent ---")
    design_data = design_agent_instance.generate_design(spec_data) # Directly call the method
    print(f"Design Generated for: {design_data['project_Overview']['project_Name']}")
    # You could then convert this design_data to a message for the next agent

except Exception as e:
    print(f"Orchestration failed: {e}")