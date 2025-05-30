# This script is act as a client for interacting with an A2A server,specifically targeting the host_agent running at http://localhost:12000/host_agent. It sends a user query to the server, receives a response, and processes the result

import asyncio
import logging
import traceback
from uuid import uuid4

# Assuming common types and client are importable
from a2a_servers.common.a2a_client import A2AClient, card_resolver # card_resolver might be needed for discovering the host_agent's capabilities via its AgentCard.
from a2a_servers.common.types import Message, TextPart, AgentCard, TaskSendParams # Import AgentCard if needed directly

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_URL = "http://localhost:12000/host_agent"

async def main():
    client = A2AClient(url=SERVER_URL)

    task_id = f"echo-task-{uuid4().hex}"
    session_id = f"session-{uuid4().hex}"
    user_text = input("Enter your query: ") # Example user input

    user_message = Message(
        role="user",
        parts=[TextPart(text=user_text)]
    )

    send_params = TaskSendParams(
        id=task_id,
        sessionId=session_id,
        message=user_message.model_dump(),
        acceptedOutputModes=["text"]
    )

    try:
        logger.info(f"Sending task {task_id} to {SERVER_URL}...")
        response = await client.send_task(payload=send_params)

        if response.error:
            logger.error(f"Task {task_id} failed: {response.error.message} (Code: {response.error.code})")
        elif response.result:
            task_result = response.result
            logger.info(f"Task {task_id} completed with state: {task_result.status.status}")
            if task_result.status.message and task_result.status.message.parts:
                 agent_part = task_result.status.message.parts[0]
                 print(agent_part.text)
            else:
                 logger.warning("No message part in agent response status")
        else:
            logger.error(f"Received unexpected response for task {task_id}: {response}")

    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"An error occurred while communicating with the agent: {e}")

if __name__ == "__main__":
    asyncio.run(main())