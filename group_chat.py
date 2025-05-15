from typing import List, Dict
import re
import asyncio
from pprint import pprint
from base_agent import BaseAgent
from models import MessageRecord
from agent_instructions import agent_instructions


class GroupChat:
    def __init__(self, name: str):
        self.name = name
        self.agents: Dict[str, BaseAgent] = {}
        self.chat_history = []
        self.running = False
        self.chat_logging = False

    # manage agents
    def add_agent(self, agent: BaseAgent) -> str:
        """Add an agent to the group chat."""
        # Generate a unique agent ID if none provided
        self.agents[agent.name] = agent
        self._system_message(f"{agent.name} has joined the chat.")
        return agent.name

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the group chat."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self._system_message(f"{agent_id} has left the chat.")
            return True

    # manage messages
    def _parse_mentions(self, message: str) -> List[str]:
        """Extract @mentions from the message."""
        pattern = r'@(\w+)'
        return re.findall(pattern, message)

    def _system_message(self, message: str):

        message_record: MessageRecord = MessageRecord(
            sender="system",
            message=f"System: {message} @all",
            receivers=["human", "system"],
        )

        self._send_to_chat(message_record)

    def _send_to_chat(self, message_record: MessageRecord) -> bool:
        """Send a message to the group chat. The message must contains at least one @mention

        Args:
            sender_id: The ID of the sender
            message: The message to send

        Returns:
            True if the message was sent successfully, False otherwise
        """
        # Ensure the message contains at least one @mention

        self.chat_history.append(message_record)
        if self.chat_logging:
            print(
                f"[LOG] From {message_record.sender} to {message_record.receivers}: {message_record.message}")
        return True

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
        """Send the message from the human to the group chat. Wrap the message with @system to mention the system agent."""
        message: MessageRecord = MessageRecord(
            sender="human",
            message=text,
            receivers=["system"],
        )
        self._send_to_chat(message)

    def _send_to_system(self, message_records: List[MessageRecord]):
        """
        Parse the messages records and send the message to the system. The system has the ability to use tools and set reminders for other agents.
        """
        for message_record in message_records:
            message = message_record.message.lower()

            # Check if this is a reminder request
            if "remind" in message:
                print(f"reminder request: {message}")

            self._read_message_records("system", [message_record])

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
                    self._send_to_chat(message)
                    self._read_message_records(agent_id, message_records)

                    print()
                except Exception as e:
                    print(f"Error sending message to {agent_id}: {e}")
                    return None

    def _find_unread_messages(self, agent_id: str) -> List[MessageRecord]:
        """Check if the agent has unread messages."""
        unread_messages: List[MessageRecord] = [
            msg for msg in self.chat_history
            if agent_id in msg.receivers and agent_id not in msg.readers
        ]
        return unread_messages

    async def _check_unread_messages(self):
        """Continuously scan for idle agents and send them unread messages."""
        while self.running:

            # TODO: change it from continuously checking to only when the human sends a message
            unread_messages = self._find_unread_messages("human")
            if unread_messages:
                self._send_to_human(unread_messages)
            await asyncio.sleep(1)

            for agent_id, agent in self.agents.items():
                # Check if agent is idle (not currently processing messages)
                if agent and not agent.is_processing:
                    unread_messages = self._find_unread_messages(agent_id)
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

        while self.running:
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
                    self.chat_logging = not self.chat_logging
                    print(
                        f"Logging {'enabled' if self.chat_logging else 'disabled'}")
                    # Restore prompt after logging message
                    print("> ", end="", flush=True)
                    continue

                # Check if user wants to exit
                elif user_input == 'EXIT':
                    return True
                elif user_input == 'REMINDERS':
                    print(self.reminder_manager.reminders)
                    continue
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
            asyncio.create_task(self._check_unread_messages())
            self.should_stop = asyncio.create_task(self.handle_human_input())

    def stop(self):
        """Stop the group chat service."""
        self.running = False
        self.reminder_manager.stop()


async def main():
    chat = GroupChat("AI Collaboration Room")
    chat.chat_logging = True
    chat.start()

    for agent_instruction in agent_instructions:
        chat.add_agent(BaseAgent(**agent_instruction))

    try:
        # Wait for the input task to complete (when user types 'exit')
        should_exit = await chat.should_stop
    finally:
        chat.stop()


if __name__ == "__main__":
    asyncio.run(main())
