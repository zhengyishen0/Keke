import threading
from typing import List, Dict, Callable, Union, Optional
import re
import datetime
import time
import asyncio
from agents import Agent, ItemHelpers, MessageOutputItem, Runner, trace, function_tool
from base_agent import BaseAgent
from models import MessageRecord
from pprint import pprint

SERVANT_INSTRUCTIONS = """
You are a helpful agent that will collaborate with human and other agents in a group chat. 
Whenever you reply, you MUST use "@" to mention a receiver of the message. By default, you will reply to a human so you should use '@human'.
If you want to send the message to other agents you can use '@agent_name' to mention a specific agents. 
You can mention all agents using '@all', 
You can also mention the system (which has the ability to reminder you a task later) using '@system'.

There are only four options for the receiver: '@human', '@all', '@agent_name', '@system'.
The agent_name is default to none unless it is specified to you.
"""

agent_instructions = [
    {"name": "servant", "instructions": SERVANT_INSTRUCTIONS}]


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
        self.agents: Dict[str, BaseAgent | None] = {
            "system": None,
            "human": None,
            "all": None
        }  # initializes with a default "all" and "human" agent
        self.chat_history = []
        self.reminders: List[Reminder] = []
        self.reminder_thread = None
        self.running = False
        self.chat_logging = False

    def enable_chat_logging(self, enable: bool):
        """Enable or disable logging of chat messages to console.

        Args:
            enable: If True, chat messages will be printed to console. If False, messages will be silent.
        """
        self.chat_logging = enable

    # manage agents
    def add_agent(self, agent: BaseAgent) -> str:
        """Add an agent to the group chat."""
        # Generate a unique agent ID if none provided
        self.agents[agent.name] = agent
        self._send_to_chat(
            "all", f"System: {agent.name} has joined the chat. @all")
        return agent.name

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the group chat."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self._send_to_chat(
                "all", f"System: {agent_id} has left the chat. @all")
            return True

    # manage messages
    def _parse_mentions(self, message: str) -> List[str]:
        """Extract @mentions from the message."""
        pattern = r'@(\w+)'
        return re.findall(pattern, message)

    def _send_to_chat(self, sender_id: str, message: str) -> bool:
        """Send a message to the group chat. The message must contains at least one @mention

        Args:
            sender_id: The ID of the sender
            message: The message to send

        Returns:
            True if the message was sent successfully, False otherwise
        """
        # Ensure the message contains at least one @mention
        receivers = self._parse_mentions(message)
        if receivers:
            # Store message in chat history
            message_record: MessageRecord = MessageRecord(
                sender=sender_id,
                message=message,
                receivers=receivers,
                readers=[]
            )
            self.chat_history.append(message_record)
            if self.chat_logging:
                print(
                    f"[LOG] From {message_record.sender} to {message_record.receivers}: {message_record.message}")
            return True
        else:
            return False

    def _send_to_human(self, message_records: List[MessageRecord]):
        """Parse the messages records and send the message to the human."""
        # Clear the prompt by printing a newline and backspace
        print("\r", end="", flush=True)
        for message_record in message_records:
            message = message_record.message.replace("@human", "").strip()
            print(message)  # Print message without newline before
        self._read_message_records("human", message_records)
        # Restore the prompt
        print("> ", end="", flush=True)

    def human_input(self, text: str):
        """Send the message from the human to the group chat. Wrap the message with @servant to mention the servant agent."""
        self._send_to_chat("human", f"@servant {text}")

    def _send_to_system(self, message_records: List[MessageRecord]):
        """
        Parse the messages records and send the message to the system. The system has the ability to use tools and set reminders for other agents.
        """
        # TODO: Implement the logic to send the message to the system.
        pass

    def _read_message_records(self, agent_id: str, message_records: List[MessageRecord]):
        for message_record in message_records:
            message_record.readers.append(agent_id)

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
                self._read_message_records(agent_id, message_records)
        else:  # send to the specific agent
            agent = self.agents.get(agent_id)
            if agent:
                try:
                    message = await agent.run(message_records=message_records)
                    self._send_to_chat(agent_id, message)
                    self._read_message_records(agent_id, message_records)

                    print()
                except Exception as e:
                    print(f"Error sending message to {agent_id}: {e}")
                    return None

    # manage reminders
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
                    asyncio.run(self._send_to_chat(
                        "Reminder_System", reminder_message))

                    # Mark for removal if time-based (one-time)
                    if reminder.trigger_type == "time":
                        triggered_reminders.append(reminder)

            # Remove triggered time-based reminders
            for reminder in triggered_reminders:
                self.reminders.remove(reminder)

            # Sleep for a short period before checking again
            time.sleep(1)

    def _check_unread_messages(self, agent_id: str):
        """Check if the agent has unread messages."""
        unread_messages = [
            msg for msg in self.chat_history
            if agent_id in msg.receivers and agent_id not in msg.readers
        ]
        return unread_messages

    async def _check_idle_agents(self):
        """Continuously scan for idle agents and send them unread messages."""
        while self.running:
            for agent_id, agent in self.agents.items():
                # Skip system and all agents
                if agent_id in ["system", "all"]:
                    continue

                # Check unread messages for human
                if agent_id == "human":
                    unread_messages = self._check_unread_messages(agent_id)
                    if unread_messages:
                        self._send_to_human(unread_messages)

                # Check if agent is idle (not currently processing messages)
                if agent and not agent.is_processing:
                    unread_messages = self._check_unread_messages(agent_id)
                    if unread_messages:
                        await self._send_to_agent(agent_id, unread_messages)

            # Sleep for a short period before checking again
            await asyncio.sleep(1)

    async def handle_human_input(self):
        """Handle continuous human input in an asynchronous way."""
        print("\nWelcome to the AI Collaboration Room! Type your messages and press Enter to send.")
        print("Type 'CHAT' to print the chat history.")
        print("Type 'LOG' to toggle logging.")
        print("Type 'EXIT' to quit the chat.\n")
        print("> ", end="", flush=True)  # Initial prompt

        while True:
            try:
                # Get input from user using asyncio.get_event_loop().run_in_executor
                loop = asyncio.get_event_loop()
                user_input = await loop.run_in_executor(None, lambda: input().strip())

                if user_input == "CHAT":
                    pprint(self.chat_history)
                    # Restore prompt after chat history
                    print("> ", end="", flush=True)
                    continue
                elif user_input == "LOG":
                    self.enable_chat_logging(not self.chat_logging)
                    print(
                        f"Logging {'enabled' if self.chat_logging else 'disabled'}")
                    # Restore prompt after logging message
                    print("> ", end="", flush=True)
                    continue

                # Check if user wants to exit
                elif user_input == 'EXIT':
                    return True
                else:
                    # Send the message to the chat
                    self.human_input(user_input)
                    # Note: prompt is restored in _send_to_human after agent response

            except KeyboardInterrupt:
                return True
            except Exception as e:
                print(f"An error occurred: {e}")
                print("> ", end="", flush=True)  # Restore prompt after error
                return False

    # start and stop the group chat
    def start(self):
        """Start the group chat service."""
        if not self.running:
            self.running = True

            self.reminder_thread = threading.Thread(
                target=self._check_reminders)
            self.reminder_thread.daemon = True
            self.reminder_thread.start()

            # Start the idle agent checking process
            asyncio.create_task(self._check_idle_agents())

    def stop(self):
        """Stop the group chat service."""
        self.running = False
        if self.reminder_thread:
            self.reminder_thread.join(timeout=2)


async def main():
    chat = GroupChat("AI Collaboration Room")
    chat.enable_chat_logging(True)
    chat.start()

    for agent_instruction in agent_instructions:
        chat.add_agent(BaseAgent(
            name=agent_instruction["name"],
            instructions=agent_instruction["instructions"]
        ))

    # Create task for handling human input
    input_task = asyncio.create_task(chat.handle_human_input())

    try:
        # Wait for the input task to complete (when user types 'exit')
        should_exit = await input_task
    finally:
        chat.stop()


if __name__ == "__main__":
    asyncio.run(main())

    # # Add a time-based reminder
    # tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    # reminder_id = chat.add_time_reminder(
    #     "researcher",
    #     "Follow up on reinforcement learning research",
    #     tomorrow
    # )

    # # Add a conditional reminder
    # def code_completed_condition():
    #     # This would check some external condition
    #     # For example, checking if a file exists or a task is marked as done
    #     return False  # Replace with actual condition

    # chat.add_conditional_reminder(
    #     "tester",
    #     "The code is ready for testing now",
    #     code_completed_condition
    # )
