"""
Reminder System - A Python program to manage reminders from a Markdown file

This program includes the following features:
- Monitor reminders and trigger notifications when conditions are met
- Add new reminders to the MD file
- Cancel/remove existing reminders
- Mark reminders as finished when triggered
- List all reminders in the MD file
"""

import os
import time
import datetime
import re
import threading
import sys
import platform
from typing import List, Dict, Optional, Union
from config import REMINDER_FILE_PATH, REMINDER_CHECK_INTERVAL


# Define the reminder status types
class ReminderStatus:
    """
    Enum for the status of a reminder\n
    PENDING | COMPLETED | CANCELLED
    """
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Reminder:
    def __init__(
        self,
        id: str,
        title: str,
        description: str = "",
        due_datetime: Optional[datetime.datetime] = None,
        status: str = ReminderStatus.PENDING,
        tags: List[str] = None
    ):
        self.id = id
        self.title = title
        self.description = description
        self.due_datetime = due_datetime
        self.status = status
        self.tags = tags or []

    def __str__(self) -> str:
        due_str = self.due_datetime.strftime(
            "%Y-%m-%d %H:%M") if self.due_datetime else "No due date"
        return f"[{self.status}] {self.id}: {self.title} - Due: {due_str}"

    def to_markdown(self) -> str:
        """Convert the reminder to markdown format"""
        md_lines = []
        md_lines.append(f"## {self.id}: {self.title}")
        md_lines.append(f"**Status:** {self.status}")

        if self.due_datetime:
            md_lines.append(
                f"**Due:** {self.due_datetime.strftime('%Y-%m-%d %H:%M')}")

        if self.tags:
            md_lines.append(f"**Tags:** {', '.join(self.tags)}")

        if self.description:
            md_lines.append("\n" + self.description)

        md_lines.append("\n---\n")
        return "\n".join(md_lines)

    @classmethod
    def from_markdown_block(cls, block_text: str) -> 'Reminder':
        """Parse a markdown block to create a Reminder object"""
        # Extract the ID and title from the header
        header_match = re.search(r'## ([\w\d-]+): (.+)', block_text)
        if not header_match:
            raise ValueError(
                f"Could not parse reminder header from: {block_text[:50]}...")

        reminder_id = header_match.group(1)
        title = header_match.group(2)

        # Extract status
        status_match = re.search(r'\*\*Status:\*\* (\w+)', block_text)
        status = status_match.group(
            1) if status_match else ReminderStatus.PENDING

        # Extract due date
        due_datetime = None
        due_match = re.search(
            r'\*\*Due:\*\* (\d{4}-\d{2}-\d{2} \d{2}:\d{2})', block_text)
        if due_match:
            due_str = due_match.group(1)
            try:
                due_datetime = datetime.datetime.strptime(
                    due_str, "%Y-%m-%d %H:%M")
            except ValueError:
                print(
                    f"Warning: Could not parse due date '{due_str}' for reminder {reminder_id}")

        # Extract tags
        tags = []
        tags_match = re.search(r'\*\*Tags:\*\* (.+)', block_text)
        if tags_match:
            tags = [tag.strip() for tag in tags_match.group(1).split(',')]

        # Extract description (everything after the metadata and before the divider)
        description = ""
        sections = block_text.split("\n\n")
        for i, section in enumerate(sections):
            if not (section.startswith("**") or section.startswith("## ") or section.strip() == "---"):
                description = section.strip()
                break

        return cls(reminder_id, title, description, due_datetime, status, tags)


def load_reminders(file_path: str = REMINDER_FILE_PATH) -> List[Reminder]:
    """Load all reminders from the markdown file"""
    with open(file_path, "r") as f:
        content = f.read()

    # Split the content by the divider and filter empty blocks
    blocks = [block.strip()
              for block in content.split("---") if block.strip()]

    # The first block is usually the header, so skip it if it doesn't contain a reminder
    if blocks and not blocks[0].startswith("## "):
        blocks = blocks[1:]

    reminders = []
    for block in blocks:
        try:
            if "##" in block:  # Only process blocks that have headers
                reminder = Reminder.from_markdown_block(block)
                reminders.append(reminder)
        except Exception as e:
            print(f"Error parsing reminder block: {str(e)}")

    return reminders


def save_reminders(reminders: List[Reminder], file_path: str = REMINDER_FILE_PATH) -> None:
    """Save all reminders to the markdown file"""
    with open(file_path, "w") as f:
        f.write(
            "# Reminders\n\nThis file contains all your reminders.\n\n---\n\n")
        for reminder in reminders:
            f.write(reminder.to_markdown())


def add_reminder(title: str, description: str = "",
                 due_datetime: Optional[Union[str, datetime.datetime]] = None,
                 tags: List[str] = None,
                 file_path: str = REMINDER_FILE_PATH) -> Reminder:
    """
    Add a new reminder to the system

    Args:
        title: str
        description: str = ""
        due_datetime: Optional[Union[str, datetime.datetime]] = None
        tags: List[str] = None
        file_path: str = REMINDERS_FILE_PATH

    Returns:
        Reminder: Reminder object
    """
    # Load current reminders
    reminders = load_reminders(file_path)

    # Generate a unique ID
    reminder_id = f"R{len(reminders) + 1:03d}"

    # Parse the due_datetime if it's a string
    if isinstance(due_datetime, str):
        try:
            due_datetime = datetime.datetime.strptime(
                due_datetime, "%Y-%m-%d %H:%M")
        except ValueError:
            print(
                f"Warning: Invalid datetime format '{due_datetime}'. Use 'YYYY-MM-DD HH:MM'")
            due_datetime = None

    # Create the reminder
    reminder = Reminder(reminder_id, title, description,
                        due_datetime, ReminderStatus.PENDING, tags)

    # Add it to the list and save
    reminders.append(reminder)
    save_reminders(reminders, file_path)

    print(f"Added reminder: {reminder}")
    return reminder


def remove_reminder(reminder_id: str, file_path: str = REMINDER_FILE_PATH) -> bool:
    """
    Remove a reminder by ID

    Args:
        reminder_id: str
        file_path: str = REMINDERS_FILE_PATH

    Returns:
        bool
    """
    reminders = load_reminders(file_path)
    original_count = len(reminders)

    reminders = [r for r in reminders if r.id != reminder_id]

    if len(reminders) < original_count:
        save_reminders(reminders, file_path)
        print(f"Removed reminder {reminder_id}")
        return True

    print(f"No reminder found with ID {reminder_id}")
    return False


def cancel_reminder(reminder_id: str, file_path: str = REMINDER_FILE_PATH) -> bool:
    """
    Cancel a reminder by ID (mark as cancelled but keep it)

    Args:
        reminder_id: str
        file_path: str = REMINDERS_FILE_PATH

    Returns:
        bool
    """
    reminders = load_reminders(file_path)

    for reminder in reminders:
        if reminder.id == reminder_id:
            reminder.status = ReminderStatus.CANCELLED
            save_reminders(reminders, file_path)
            print(f"Cancelled reminder {reminder_id}")
            return True

    print(f"No reminder found with ID {reminder_id}")
    return False


def complete_reminder(reminder_id: str, file_path: str = REMINDER_FILE_PATH) -> bool:
    """
    Mark a reminder as completed

    Args:
        reminder_id: str
        file_path: str = REMINDERS_FILE_PATH

    Returns:
        bool
    """
    reminders = load_reminders(file_path)

    for reminder in reminders:
        if reminder.id == reminder_id:
            reminder.status = ReminderStatus.COMPLETED
            save_reminders(reminders, file_path)
            print(f"Completed reminder {reminder_id}")
            return True

    print(f"No reminder found with ID {reminder_id}")
    return False


def list_reminders(status_filter: Optional[str] = None,
                   tag_filter: Optional[str] = None,
                   file_path: str = REMINDER_FILE_PATH) -> List[Reminder]:
    """
    List reminders, optionally filtered by status or tag

    Args:
        status_filter: Optional[str] = None
        tag_filter: Optional[str] = None
        file_path: str = REMINDERS_FILE_PATH

    Returns:
        List[Reminder]
    """
    reminders = load_reminders(file_path)
    filtered_reminders = reminders

    if status_filter:
        filtered_reminders = [
            r for r in filtered_reminders if r.status == status_filter]

    if tag_filter:
        filtered_reminders = [
            r for r in filtered_reminders if tag_filter in r.tags]

    for reminder in filtered_reminders:
        print(reminder)

    return filtered_reminders


class ReminderManager:
    def __init__(self, file_path: str = REMINDER_FILE_PATH, check_interval: int = REMINDER_CHECK_INTERVAL):
        self.file_path = file_path
        self.check_interval = check_interval
        self._ensure_file_exists()
        self._monitor_thread = None
        self._stop_monitoring = threading.Event()

    def _ensure_file_exists(self) -> None:
        """Make sure the reminders file exists, create it if not"""
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                f.write(
                    "# Reminders\n\nThis file contains all your reminders.\n\n---\n\n")
            print(f"Created new reminders file at {self.file_path}")

    def _show_notification(self, reminder: Reminder) -> None:
        """Display a system notification for the reminder"""
        title = f"Reminder: {reminder.title}"
        message = reminder.description if reminder.description else "Time to complete this task!"

        # Print to console
        print("\n" + "-" * 50)
        print(f"REMINDER ALERT: {title}")
        print(message)
        print("-" * 50 + "\n")

        # Try to show a system notification
        try:
            if platform.system() == "Windows":
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=10)
            elif platform.system() == "Darwin":  # macOS
                os.system(
                    f"""osascript -e 'display notification "{message}" with title "{title}"'""")
            elif platform.system() == "Linux":
                os.system(f"""notify-send "{title}" "{message}" """)
        except Exception as e:
            print(f"Could not display system notification: {e}")

    def _check_due_reminders(self) -> None:
        """Check for reminders that are due and trigger notifications"""
        now = datetime.datetime.now()
        reminders = load_reminders(self.file_path)

        for reminder in reminders:
            if (reminder.status == ReminderStatus.PENDING and
                reminder.due_datetime and
                    reminder.due_datetime <= now):

                self._show_notification(reminder)

    def start(self) -> None:
        """Start monitoring reminders in a background thread"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            print("Monitoring is already active")
            return

        self._stop_monitoring.clear()

        def monitor_loop():
            print(
                f"Monitoring reminders (checking every {self.check_interval} seconds)...")
            while not self._stop_monitoring.is_set():
                try:
                    # Check reminders directly from file
                    self._check_due_reminders()
                except Exception as e:
                    print(f"Error while checking reminders: {e}")

                # Sleep for the interval but be responsive to stop signals
                self._stop_monitoring.wait(self.check_interval)

        self._monitor_thread = threading.Thread(
            target=monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self) -> None:
        """Stop the reminder monitoring thread"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._stop_monitoring.set()
            self._monitor_thread.join(timeout=1.0)
            print("Reminder monitoring stopped")
        else:
            print("Monitoring is not active")


def print_help() -> None:
    """Print the available commands"""
    print("\nReminder System Commands:")
    print("  add <title> [due_datetime] [description] [tags]")
    print("      - Add a new reminder")
    print("      - due_datetime format: YYYY-MM-DD HH:MM")
    print("      - tags format: tag1,tag2,tag3")
    print("  list [status] [tag]")
    print("      - List all reminders, optionally filtered by status or tag")
    print("  complete <id>")
    print("      - Mark a reminder as completed")
    print("  cancel <id>")
    print("      - Mark a reminder as cancelled")
    print("  remove <id>")
    print("      - Delete a reminder completely")
    print("  monitor [interval]")
    print("      - Start monitoring reminders (interval in seconds, default 60)")
    print("  stop")
    print("      - Stop monitoring reminders")
    print("  exit")
    print("      - Exit the program")
    print("  help")
    print("      - Show this help message")


def parse_add_args(args: str) -> tuple[str, str, Optional[Union[str, datetime.datetime]], List[str]]:
    """Parse arguments for the add command.

    Args:
        args: The command arguments string

    Returns:
        tuple containing (title, description, due_datetime, tags)
    """
    title_parts = args.split(" ", 1)
    title = title_parts[0]

    # Check if there are more arguments
    if len(title_parts) > 1:
        # Try to parse due_datetime, description, and tags
        remaining = title_parts[1].strip()

        # Check for datetime format
        due_datetime = None
        datetime_match = re.search(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2})', remaining)
        if datetime_match:
            due_datetime = datetime_match.group(1)
            remaining = remaining.replace(due_datetime, "").strip()

        # Check for tags
        tags = []
        tags_match = re.search(r'tags:([a-zA-Z0-9,]+)', remaining)
        if tags_match:
            tags_str = tags_match.group(1)
            tags = [tag.strip() for tag in tags_str.split(',')]
            remaining = remaining.replace(f"tags:{tags_str}", "").strip()

        # The rest is the description
        description = remaining if remaining else ""
    else:
        due_datetime = None
        description = ""
        tags = []

    return title, description, due_datetime, tags


def parse_list_args(args: str) -> tuple[Optional[str], Optional[str]]:
    """Parse arguments for the list command.

    Args:
        args: The command arguments string

    Returns:
        tuple containing (status_filter, tag_filter)
    """
    status_filter = None
    tag_filter = None

    if args:
        args_parts = args.split()
        for arg in args_parts:
            if arg.upper() in [ReminderStatus.PENDING, ReminderStatus.COMPLETED, ReminderStatus.CANCELLED]:
                status_filter = arg.upper()
            else:
                tag_filter = arg

    return status_filter, tag_filter


def parse_command(command: str) -> tuple[str, str]:
    """Parse the command string into command and arguments.

    Args:
        command: The full command string entered by user

    Returns:
        tuple containing (command, arguments)
    """
    if not command:
        return "", ""

    parts = command.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    return cmd, args


def main() -> None:
    """Main function to run the reminder system"""
    print("Welcome to the Reminder System!")
    print_help()

    manager = ReminderManager()
    manager.start()

    while True:
        try:
            command = input("\nEnter command: ").strip()
            cmd, args = parse_command(command)

            if not cmd:
                continue

            if cmd == "add":
                title, description, due_datetime, tags = parse_add_args(args)
                add_reminder(title, description, due_datetime, tags)

            elif cmd == "complete":
                complete_reminder(args)

            elif cmd == "list":
                status_filter, tag_filter = parse_list_args(args)
                list_reminders(status_filter, tag_filter)

            elif cmd == "cancel":
                cancel_reminder(args)

            elif cmd == "remove":
                remove_reminder(args)

            elif cmd == "stop":
                manager.stop()

            elif cmd == "help":
                print_help()

            elif cmd == "exit":
                print("Exiting Reminder System. Goodbye!")
                sys.exit(0)

            else:
                print(f"Unknown command: {cmd}")
                print_help()

        except KeyboardInterrupt:
            print("\nExiting Reminder System. Goodbye!")
            sys.exit(0)

        except Exception as e:
            print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
