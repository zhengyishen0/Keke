import datetime
import time
import threading
from typing import Callable, Union, Optional


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
    def __init__(self):
        self.reminders = []
        self.running = False
        self.reminder_thread = None

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

    def _check_reminders(self, callback):
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
            time.sleep(1)

    def start(self, callback):
        """Start the reminder service."""
        if not self.running:
            self.running = True
            self.reminder_thread = threading.Thread(
                target=self._check_reminders,
                args=(callback,)
            )
            self.reminder_thread.daemon = True
            self.reminder_thread.start()

    def stop(self):
        """Stop the reminder service."""
        self.running = False
        if self.reminder_thread:
            self.reminder_thread.join(timeout=2)
