import threading
from typing import List, Dict, Callable, Union, Optional
import re
import datetime
import time
import asyncio
from pydantic import BaseModel, Field

from agents import Agent, ItemHelpers, MessageOutputItem, Runner, trace, function_tool
from base_agent import BaseAgent


class MessageRecord(BaseModel):
    """A message record in the group chat.

    Attributes:
        sender: The ID of the message sender
        message: The content of the message
        timestamp: When the message was sent
        receivers: List of agent IDs mentioned in the message
        readers: List of agent IDs that have read the message
    """
    sender: str
    message: str
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    receivers: List[str] = Field(default_factory=list)
    readers: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


agent_instructions = [{"name": "Driver", "instructions": "You are an expert driver that can drive a car."},
                      {"name": "Researcher", "instructions": "You are an expert researcher that can find information about a given topic."},
                      {"name": "Coder", "instructions": "You are an expert coder that can code a given task."},
                      {"name": "Tester", "instructions": "You are an expert tester that can test a given task."}]


class Reminder:
    def __init__(self,
                 agent_id: str,
                 message: str,
                 trigger_type: str,
                 trigger_value: Union[datetime.datetime, Callable],
                 reminder_id: Optional[str] = None):
        self.agent_id = agent_id
        self.message = message
        self.trigger_type = trigger_type  # "time" or "condition"
        self.trigger_value = trigger_value
        self.reminder_id = reminder_id or f"reminder_{int(time.time())}_{agent_id}"
        self.is_active = True

    def should_trigger(self) -> bool:
        if not self.is_active:
            return False

        if self.trigger_type == "time":
            return datetime.datetime.now() >= self.trigger_value
        elif self.trigger_type == "condition":
            # For condition-based reminders, trigger_value is a callable that returns True/False
            return self.trigger_value()
        return False


class GroupChat:
    def __init__(self, name: str):
        self.name = name
        self.agents: Dict[str, BaseAgent | None] = [
            {"system": None},
            {"human": None},
            {"all": None}]  # initializes with a default "all" and "human" agent
        self.chat_history = []
        self.reminders: List[Reminder] = []
        self.reminder_thread = None
        self.running = False

    def add_agent(self, agent: BaseAgent) -> str:
        """Add an agent to the group chat."""
        # Generate a unique agent ID if none provided
        agent_id = f"{agent.name}_{len(self.agents)}"
        self.agents[agent_id] = agent
        self.send_to_chat(
            "all", f"System: {agent_id} has joined the chat. @all")
        return agent_id

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the group chat."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.send_to_chat(
                "all", f"System: {agent_id} has left the chat. @all")
            return True

    def _parse_mentions(self, message: str) -> List[str]:
        """Extract @mentions from the message."""
        pattern = r'@(\w+)'
        return re.findall(pattern, message)

    def send_to_chat(self, sender_id: str, message: str) -> bool:
        """Send a message to the group chat. The message must contains at least one @mention

        Args:
            sender_id: The ID of the sender
            message: The message to send

        Returns:
            True if the message was sent successfully, False otherwise
        """

        # Ensure the message contains at least one @mention
        receivers = self._parse_mentions(message)
        print(f"Receivers: {receivers}")
        if receivers:
            # Store message in chat history
            message_record: MessageRecord = MessageRecord(
                sender=sender_id,
                message=message,
                receivers=receivers,
                readers=[]
            )
            self.chat_history.append(message_record)
            return True
        else:
            return False

    def _send_to_human(self, message_records: List[MessageRecord]):
        """Parse the messages records and send the message to the human."""
        # TODO: Implement the logic to send the message to the human.
        pass

    def _send_to_system(self, message_records: List[MessageRecord]):
        """
        Parse the messages records and send the message to the system. The system has the ability to use tools and set reminders for other agents.
        """
        # TODO: Implement the logic to send the message to the system.
        pass

    async def _send_to_agent(self, agent_id: str, message_records: List[MessageRecord]):
        """Send all the unread messages that mention the agent to the agent.

        Args:
            agent_id: The ID of the agent to send the message to
            message_records: A list of message records to send
        """

        if agent_id == "all":  # If the agent_id is "all", send to all agents
            for agent_id in self.agents:
                asyncio.create_task(self._send_to_agent(
                    agent_id, message_records))
        elif agent_id == "system":
            pass
        elif agent_id == "human":
            self._send_to_human(message_records)
        else:  # send to the specific agent
            agent = self.agents.get(agent_id)
            if agent:
                try:
                    message = await agent.handle_text_input(message_records=message_records)
                    self.send_to_chat(agent_id, message)
                except Exception as e:
                    print(f"Error sending message to {agent_id}: {e}")
                    return None

    def add_time_reminder(self, agent_id: str, message: str, trigger_time: datetime.datetime) -> str:
        """Add a time-based reminder."""
        reminder = Reminder(
            agent_id=agent_id,
            message=message,
            trigger_type="time",
            trigger_value=trigger_time
        )
        self.reminders.append(reminder)
        return reminder.reminder_id

    def add_conditional_reminder(self, agent_id: str, message: str, condition: Callable) -> str:
        """Add a condition-based reminder."""
        reminder = Reminder(
            agent_id=agent_id,
            message=message,
            trigger_type="condition",
            trigger_value=condition
        )
        self.reminders.append(reminder)
        return reminder.reminder_id

    def cancel_reminder(self, reminder_id: str) -> bool:
        """Cancel a reminder by ID."""
        for reminder in self.reminders:
            if reminder.reminder_id == reminder_id:
                reminder.is_active = False
                return True
        return False

    def _check_reminders(self):
        """Check if any reminders should be triggered."""
        while self.running:
            triggered_reminders = []

            for reminder in self.reminders:
                if reminder.should_trigger():
                    # Prepare the reminder message with @mention
                    reminder_message = f"REMINDER for @{reminder.agent_id}: {reminder.message}"

                    # Send the reminder
                    asyncio.run(self.send_to_chat(
                        "Reminder_System", reminder_message))

                    # Mark for removal if time-based (one-time)
                    if reminder.trigger_type == "time":
                        triggered_reminders.append(reminder)

            # Remove triggered time-based reminders
            for reminder in triggered_reminders:
                self.reminders.remove(reminder)

            # Sleep for a short period before checking again
            time.sleep(1)

    def start(self):
        """Start the group chat service."""
        if not self.running:
            self.running = True
            self.reminder_thread = threading.Thread(
                target=self._check_reminders)
            self.reminder_thread.daemon = True
            self.reminder_thread.start()

    def stop(self):
        """Stop the group chat service."""
        self.running = False
        if self.reminder_thread:
            self.reminder_thread.join(timeout=2)


# Example usage
async def example_usage():
    # Create a group chat
    chat = GroupChat("AI Collaboration Room")

    # Start the chat service
    chat.start()

    # Add agents
    for agent_instruction in agent_instructions:
        chat.add_agent(BaseAgent(
            name=agent_instruction["name"],
            instructions=agent_instruction["instructions"]
        ))

    # Send a message
    await chat.send_to_chat("human", "Hey @researcher, can you find information about reinforcement learning?")

    # Add a time-based reminder
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    reminder_id = chat.add_time_reminder(
        "researcher",
        "Follow up on reinforcement learning research",
        tomorrow
    )

    # Add a conditional reminder
    def code_completed_condition():
        # This would check some external condition
        # For example, checking if a file exists or a task is marked as done
        return False  # Replace with actual condition

    chat.add_conditional_reminder(
        "tester",
        "The code is ready for testing now",
        code_completed_condition
    )

    # In a real app, you would keep the service running
    # For this example, we'll just sleep briefly
    await asyncio.sleep(5)

    # Stop the service
    chat.stop()

# Run the example
if __name__ == "__main__":
    asyncio.run(example_usage())
