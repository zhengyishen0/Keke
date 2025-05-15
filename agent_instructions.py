from models import MessageRecord
from agents import function_tool
import time


@function_tool
def add_reminder(agent_id: str, message: str, trigger_type: str, trigger_value: str) -> str:
    """Add a reminder to the reminder manager.
    Args:
        agent_id: The ID of the agent to send the reminder to
        message: The message to send to the agent
        trigger_type: The type of trigger to use for the reminder (time or condition)
        trigger_value: The value to use for the trigger (ISO format datetime for time type)

    Returns:
        str: The ID of the created reminder
    """
    print(
        f"add_reminder request: {agent_id}, {message}, {trigger_type}, {trigger_value}")

    # Get access to the reminder manager
    # Note: This is a placeholder - we need to implement a way to access the group chat instance
    # This will be implemented later when we add proper state management

    # For now, just return a dummy reminder ID
    return f"reminder_{int(time.time())}_{agent_id}"


SYSTEM_INSTRUCTIONS = """
You are a helpful agent that will collaborate with human and other agents in a group chat.
Whenever you reply, specify the receiver of the message in the message record.

output_type: MessageRecord
sender: str = "system"
message: str = "the message content"
receivers: List[str] = receiver_names (you can chose from "human" or "specific_agent_name")

"""

agent_instructions = [
    {"name": "system", "instructions": SYSTEM_INSTRUCTIONS, "output_type": MessageRecord, "tools": [add_reminder]}]
