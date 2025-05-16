import datetime
import time
import asyncio
from typing import Callable, Union, Optional, List
from agents import function_tool


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


class ReminderManager:
    # singleton pattern
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ReminderManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.reminders = []
            self.running = False
            self.check_task = None
            self._initialized = True

    async def _check_reminders(self, callback):
        """Check if any reminders should be triggered."""
        while self.running:
            triggered_reminders = []

            for reminder in self.reminders:
                if reminder.should_trigger():
                    reminder_message = f"REMINDER for @{reminder.agent_id}: {reminder.message}"
                    callback(reminder_message)

                    # Mark for removal if time-based (one-time)
                    if reminder.trigger_type == "time":
                        triggered_reminders.append(reminder)

            # Remove triggered time-based reminders
            for reminder in triggered_reminders:
                self.reminders.remove(reminder)

            # Sleep for a short period before checking again
            await asyncio.sleep(1)

    def start(self, callback) -> bool:
        """Start the reminder service."""
        if not self.running:
            self.running = True
            self.check_task = asyncio.create_task(
                self._check_reminders(callback))
            return True
        return False

    async def stop(self) -> bool:
        """Stop the reminder service."""
        if self.running:
            self.running = False
            if self.check_task:
                await self.check_task
                self.check_task = None
                return True
        return False


# Create a singleton instance of ReminderManager
reminder_manager = ReminderManager()


# @function_tool
def add_reminder(
    agent_id: str,
    message: str,
    trigger_type: str,
    trigger_value: Union[str, Callable]
) -> str:
    """Add a reminder (either time-based or condition-based).

    Args:
        agent_id: The ID of the agent to send the reminder to
        message: The message to send to the agent
        trigger_type: Type of trigger - either "time" or "condition"
        trigger_value: For time triggers: ISO format datetime string (YYYY-MM-DDTHH:MM:SS)
                      For condition triggers: A callable that returns True/False

    Returns:
        The ID of the created reminder
    """
    if trigger_type == "time" and isinstance(trigger_value, str):
        trigger_value = datetime.datetime.fromisoformat(trigger_value)

    reminder = Reminder(
        agent_id=agent_id,
        message=message,
        trigger_type=trigger_type,
        trigger_value=trigger_value
    )
    reminder_manager.reminders.append(reminder)
    print(
        f"Reminder added: {reminder.reminder_id}, {reminder.message}, {reminder.trigger_type}, {reminder.trigger_value}")
    return reminder.reminder_id


# @function_tool
def cancel_reminder(reminder_id: str) -> bool:
    """Cancel a reminder by ID.

    Args:
        reminder_id: The ID of the reminder to cancel

    Returns:
        True if reminder was found and cancelled, False otherwise
    """
    for reminder in reminder_manager.reminders:
        if reminder.reminder_id == reminder_id:
            reminder.is_active = False
            return True
    return False


# @function_tool
def check_reminders() -> List[str]:
    """Check active reminders in the queue."""
    reminders = [
        reminder.reminder_id for reminder in reminder_manager.reminders if reminder.is_active]
    print(f"Active reminders: {reminders}")
    return reminders


async def main():
    """Test the reminder manager functionality."""
    # Create a test callback function
    # def reminder_callback(message: str):
    #     print(f"Callback received: {message}")

    # # Start the reminder manager
    # reminder_manager.start(reminder_callback)

    # Add a reminder that will trigger in 5 seconds
    reminder_id = add_reminder("system", "This is a test reminder", "time",
                               (datetime.datetime.now() + datetime.timedelta(seconds=5)).isoformat())
    print("\nAdded reminder. Current reminders:")
    check_reminders()

    await asyncio.sleep(10)

    # Stop the reminder manager
    await reminder_manager.stop()
    print("\nReminder manager stopped.")


if __name__ == "__main__":
    asyncio.run(main())
