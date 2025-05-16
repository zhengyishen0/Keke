import time
import datetime
import os
import re
from typing import List
import uuid  # For parsing the markdown file
import threading
from enum import Enum
from config import REMINDER_FILE_PATH, REMINDER_CHECK_INTERVAL


class ReminderStatus(Enum):
    PENDING = "pending"
    TRIGGERED = "triggered"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class Reminder:
    """
    A class to represent a reminder.
    Attributes:
        id: The ID of the reminder.
        task: The description of the reminder.
        due_str: The due date and time of the reminder in the format "YYYY-MM-DD HH:MM"
        status: The status of the reminder. Can be "pending", "triggered", "finished", "cancelled"
        condition: The condition of the reminder. Can be "on_time", "late", "missed"
    """

    def __init__(self, id: str, task: str, due_str: str, status: str, condition: str):
        self.checked = False
        self.id = id
        self.task = task
        self.due_str = due_str
        self.status = ReminderStatus(status)
        self.condition = condition


def parse_reminder_line(line: str) -> Reminder | None:
    """
    Parses a single line from the reminder file.

    # Format: - [ ] | ID | Task Description | Due DateTime (YYYY-MM-DD HH:MM) | Status | Condition
    # Example: - [ ] | 1234567890 | Buy groceries | 2023-01-01 12:00 | pending | 

    """
    match = re.match(
        r"- \[( |x)\] \| (.*?) \| (.*?) \| (.*?) \| (.*?)( \| (.*?))?$", line)

    if match:
        parts = [p.strip() for p in match.groups()]
        return Reminder(
            id=parts[1],
            task=parts[2],
            due_str=parts[3],
            status=parts[4],
            condition=parts[5]
        )
    return None


def ensure_reminder_file_exists() -> bool:
    """
    Checks if the reminder file exists.

    Returns:
        bool: True if the reminder file exists, False otherwise.
    """
    if not os.path.exists(REMINDER_FILE_PATH):
        print(
            f"Reminder file not found. Creating new file at {REMINDER_FILE_PATH}")
        with open(REMINDER_FILE_PATH, "w") as f:
            f.write("# Reminders\n\n")
        return False
    return True


def get_reminders() -> List[Reminder]:
    """
    Reads and parses all reminders from the markdown file.
    create the file if it doesn't exist

    Args:
        None

    Returns:
        list: A list of reminders
    """
    reminders = []
    if not ensure_reminder_file_exists():
        print(
            f"Reminder file not found. Creating new file at {REMINDER_FILE_PATH}")
        return reminders
    with open(REMINDER_FILE_PATH, "r") as f:
        for line in f:
            reminder = parse_reminder_line(line.strip())
            if reminder:
                reminders.append(reminder)
    return reminders


def save_reminders_to_markdown(reminders: List[Reminder]) -> bool:
    """
    Saves a list of reminders into a markdown file following the format

    # Format:  - [ ] | ID | Task Description | Due DateTime (YYYY-MM-DD HH:MM) | Status | Condition
    """

    header = "# Reminders\n\n"
    body = "\n".join(
        [f"- [{'x' if reminder.checked else ' '}] | {reminder.id} | {reminder.task} | {reminder.due_str} | {reminder.status.value} | {reminder.condition}" for reminder in reminders])
    try:
        with open(REMINDER_FILE_PATH, "w") as f:
            f.write(header + body)
        return True
    except Exception as e:
        print(f"Error saving reminders to markdown: {e}")
        return False


def notify_user(reminder):
    """Displays a notification to the user."""
    # Simple print notification. You can expand this with system notifications.
    print("*" * 40)
    print(f"🔔 REMINDER 🔔")
    print(f"Task: {reminder.task}")
    print(f"Due: {reminder.due_str}")
    print("*" * 40)
    # Potentially call a function to mark as 'triggered' in the md file
    # For simplicity, we'll just print here. The 'finish' function will update the file.


def update_reminder(reminder_id: str, new_status: ReminderStatus | None = None, new_checked_state: bool | None = None) -> bool:
    """
    Updates the status or checked state of a reminder in the md file.

    Args:
        reminder_id: The ID of the reminder to update.
        new_status: The new status of the reminder. Can be "pending", "triggered", "finished"
        new_checked_state: The new checked state of the reminder. Can be True or False

    Returns:
        bool: True if the reminder was updated, False otherwise.
    """
    reminders = get_reminders()
    updated = False

    if new_status is None and new_checked_state is None:
        raise ValueError("new_status or new_checked_state must be provided")

    for reminder in reminders:
        if reminder.id == reminder_id:
            reminder.status = new_status
            reminder.checked = new_checked_state
            updated = True
            break

    if updated:
        save_reminders_to_markdown(reminders)
    return updated


def add_reminder(task_description: str, due_datetime_str: str) -> bool:
    """
    Adds a reminder to the reminder file.
    Args:
        task_description: The description of the reminder.
        due_datetime_str: The due date and time of the reminder in the format "YYYY-MM-DD HH:MM"

    Returns:
        bool: True if the reminder was added, False otherwise.
    """
    ensure_reminder_file_exists()

    reminder_id = str(uuid.uuid4().hex[:10])  # Shorter unique ID
    new_reminder_line = f"\n- [ ] | {reminder_id} | {task_description} | {due_datetime_str} | pending | none \n"

    with open(REMINDER_FILE_PATH, "a") as f:
        f.write(new_reminder_line)
    print(f"Reminder added: '{task_description}' with ID {reminder_id}")
    return True


class ReminderMonitor:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._lock = threading.Lock()

    def start(self):
        """Start the reminder monitor in a separate thread."""
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._monitor_loop)
            self._thread.daemon = True  # Thread will exit when main program exits
            self._thread.start()
            print("Reminder monitor started in background thread.")

    def stop(self):
        """Stop the reminder monitor thread."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join()
            print("Reminder monitor stopped.")

    def _monitor_loop(self):
        """Main monitoring loop that runs in a separate thread."""
        while not self._stop_event.is_set():
            try:
                with self._lock:  # Ensure thread-safe file operations
                    now = datetime.datetime.now()
                    reminders = get_reminders()

                    for reminder in reminders:
                        if reminder.status == ReminderStatus.PENDING:
                            try:
                                due_time = datetime.datetime.strptime(
                                    reminder.due_str, "%Y-%m-%d %H:%M")
                                if now >= due_time:
                                    notify_user(reminder)
                                    update_reminder(
                                        reminder.id, ReminderStatus.TRIGGERED)
                                    print(
                                        f"Reminder '{reminder.task}' triggered. Use 'finish' command to mark as done.")
                            except ValueError:
                                print(
                                    f"Warning: Could not parse due date for reminder: {reminder.task}")
                            except Exception as e:
                                print(
                                    f"An error occurred with reminder {reminder.id}: {e}")

            except Exception as e:
                print(f"Error in monitor loop: {e}")

            # Sleep with periodic checks for stop event
            for _ in range(REMINDER_CHECK_INTERVAL):
                if self._stop_event.is_set():
                    break
                time.sleep(1)


# Create a global monitor instance
reminder_monitor = ReminderMonitor()


def main_monitor():
    """Start the reminder monitor in a separate thread."""
    try:
        reminder_monitor.start()
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        reminder_monitor.stop()
        print("\nReminder monitor stopped.")


def display_menu():
    """Display the main menu options."""
    print("\n=== Reminder Manager ===")
    print("add. Add new reminder")
    print("list. List all reminders")
    print("finish. Mark reminder as finished")
    print("cancel. Cancel reminder")
    print("exit. Exit")
    print("=====================")


def list_reminders():
    """Display all reminders in a formatted way."""
    reminders = get_reminders()
    if not reminders:
        print("\nNo reminders found.")
        return

    print("\nCurrent Reminders:")
    print("-" * 80)
    print(f"{'ID':<10} {'Status':<10} {'Due Date':<20} {'Task':<30}")
    print("-" * 80)

    for reminder in reminders:
        status_icon = {
            ReminderStatus.PENDING: "⏳",
            ReminderStatus.TRIGGERED: "🔔",
            ReminderStatus.FINISHED: "✅",
            ReminderStatus.CANCELLED: "❌"
        }.get(reminder.status, "?")

        print(
            f"{reminder.id:<10} {status_icon:<10} {reminder.due_str:<20} {reminder.task:<30}")


def add_reminder_interactive():
    """Interactive function to add a new reminder.
    due_datetime_str: The due date and time of the reminder in the format "YYYY-MM-DD HH:MM"
    """
    print("\nAdd New Reminder")
    print("---------------")

    task = input("Enter task description: ").strip()
    if not task:
        print("Task description cannot be empty.")
        return

    while True:
        due_datetime = input("Enter due date (YYYY-MM-DD HH:MM): ").strip()
        try:
            datetime.datetime.strptime(due_datetime, "%Y-%m-%d %H:%M")
            break
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD HH:MM.")

    if add_reminder(task, due_datetime):
        print("Reminder added successfully!")
    else:
        print("Failed to add reminder.")


def mark_reminder_finished():
    """Interactive function to mark a reminder as finished."""
    list_reminders()
    reminder_id = input(
        "\nEnter the ID of the reminder to mark as finished: ").strip()

    if update_reminder(reminder_id, ReminderStatus.FINISHED, True):
        print("Reminder marked as finished!")
    else:
        print("Failed to update reminder. Make sure the ID is correct.")


def cancel_reminder():
    """Interactive function to cancel a reminder."""
    list_reminders()
    reminder_id = input("\nEnter the ID of the reminder to cancel: ").strip()

    if update_reminder(reminder_id, ReminderStatus.CANCELLED, True):
        print("Reminder cancelled!")
    else:
        print("Failed to cancel reminder. Make sure the ID is correct.")


def main():
    """Main function to run the reminder manager."""
    print("Starting Reminder Manager...")
    reminder_monitor.start()

    while True:
        display_menu()
        choice = input(
            "\nEnter your choice (add, list, finish, cancel, exit): ").strip()

        try:
            if choice == "add":
                add_reminder_interactive()
            elif choice == "list":
                list_reminders()
            elif choice == "finish":
                mark_reminder_finished()
            elif choice == "cancel":
                cancel_reminder()
            elif choice == "exit":
                print("\nShutting down Reminder Manager...")
                reminder_monitor.stop()
                break
            else:
                print("Invalid choice. Please enter a number between 1 and 5.")
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
