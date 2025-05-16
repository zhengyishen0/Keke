import os
import sys
import time
import shutil
import datetime
import re
import threading
import platform
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class ObsidianTaskManager:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.task_dir = self.base_dir / "Task"
        self.template_dir = self.base_dir / "Template"
        self.template_file = self.template_dir / "task.md"

        # Ensure directories exist
        self.task_dir.mkdir(exist_ok=True)
        self.template_dir.mkdir(exist_ok=True)

        # Verify template exists
        if not self.template_file.exists():
            print(f"Error: Template file not found at {self.template_file}")
            print("Please create a template file first.")
            sys.exit(1)

    def create_task(self, title, due_date=None):
        """Create a new task from template"""
        # Read template from file
        try:
            with open(self.template_file, 'r') as f:
                template = f.read()
        except Exception as e:
            print(f"Error reading template file: {e}")
            return None

        # Replace placeholders
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task_content = template.replace("{{date}}", now)
        task_content = task_content.replace("{{title}}", title)

        if due_date:
            # Validate and format due date
            try:
                # Try to parse the date to validate format
                datetime.datetime.strptime(due_date, "%Y-%m-%d %H:%M:%S")
                task_content = task_content.replace(
                    "YYYY-MM-DD HH:MM:SS", due_date)
            except ValueError:
                print("Invalid date format. Using template default.")

        # Create filename (sanitize title for use as filename)
        safe_title = "".join(
            c if c.isalnum() or c in " -_" else "_" for c in title)
        safe_title = safe_title.strip().replace(" ", "_")
        task_file = self.task_dir / f"{safe_title}.md"

        # Write task file
        with open(task_file, 'w') as f:
            f.write(task_content)

        print(f"Created task: {title}")
        return task_file.name

    def delete_task(self, task_name):
        """Delete a task by filename or title"""
        task_file = self._get_task_file(task_name)
        if task_file and task_file.exists():
            task_file.unlink()
            print(f"Deleted task: {task_file.name}")
            return True
        else:
            print(f"Task not found: {task_name}")
            return False

    def complete_task(self, task_name):
        """Mark a task as complete"""
        task_file = self._get_task_file(task_name)
        if task_file and task_file.exists():
            with open(task_file, 'r') as f:
                content = f.read()

            # Update status in frontmatter
            content = re.sub(r'status: pending', 'status: completed', content)

            # Add completion timestamp
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if "completed:" not in content:
                content = content.replace("---\n", f"---\ncompleted: {now}\n")

            with open(task_file, 'w') as f:
                f.write(content)

            print(f"Completed task: {task_file.name}")
            return True
        else:
            print(f"Task not found: {task_name}")
            return False

    def list_tasks(self, filter_status=None):
        """List all tasks, optionally filtered by status"""
        tasks = []

        for task_file in self.task_dir.glob("*.md"):
            task_info = self._parse_task_file(task_file)
            if filter_status is None or task_info.get('status') == filter_status:
                tasks.append(task_info)

        # Sort by due date if available
        tasks.sort(key=lambda x: x.get('due', '9999-99-99'))

        if not tasks:
            print("No tasks found" +
                  (f" with status: {filter_status}" if filter_status else ""))
        else:
            print(f"\n{'Title':<30} {'Status':<10} {'Due Date':<20}")
            print("-" * 60)
            for task in tasks:
                print(
                    f"{task['title']:<30} {task['status']:<10} {task.get('due', 'Not set'):<20}")

        return tasks

    def _get_task_file(self, task_name):
        """Find task file by name or title"""
        # First try exact filename match
        if not task_name.endswith('.md'):
            task_name += '.md'

        task_file = self.task_dir / task_name
        if task_file.exists():
            return task_file

        # Try to find by title in content
        for file in self.task_dir.glob("*.md"):
            task_info = self._parse_task_file(file)
            if task_info.get('title', '').lower() == task_name.replace('.md', '').lower():
                return file

        return None

    def _parse_task_file(self, file_path):
        """Extract task information from a markdown file"""
        task_info = {
            'filename': file_path.name,
            'path': str(file_path),
            # Default title from filename
            'title': file_path.stem.replace('_', ' ')
        }

        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Extract frontmatter
            frontmatter_match = re.search(
                r'---\n(.*?)\n---', content, re.DOTALL)
            if frontmatter_match:
                frontmatter = frontmatter_match.group(1)
                # Extract key metadata
                for line in frontmatter.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        task_info[key.strip()] = value.strip()

            # Extract actual title
            title_match = re.search(r'# (.*)', content)
            if title_match:
                task_info['title'] = title_match.group(1)

            # Extract notes section if present
            notes_match = re.search(
                r'## Notes\s+(.*?)(?=\n##|\Z)', content, re.DOTALL)
            if notes_match:
                task_info['notes'] = notes_match.group(1).strip()

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

        return task_info

    def get_due_tasks(self):
        """Get all tasks that are due now or in the past and still pending"""
        now = datetime.datetime.now()
        due_tasks = []

        for task_file in self.task_dir.glob("*.md"):
            task_info = self._parse_task_file(task_file)

            # Skip if not pending or no due date
            if task_info.get('status') != 'pending' or 'due' not in task_info:
                continue

            due_str = task_info.get('due')
            if due_str == 'YYYY-MM-DD HH:MM:SS':  # Skip template default
                continue

            try:
                due_time = datetime.datetime.strptime(
                    due_str, "%Y-%m-%d %H:%M:%S")
                if due_time <= now:
                    due_tasks.append(task_info)
            except ValueError:
                continue  # Skip invalid date formats

        return due_tasks


class TaskWatcher(FileSystemEventHandler):
    """File system watcher for task directory"""

    def __init__(self, task_manager):
        self.task_manager = task_manager

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.md'):
            print(f"File changed: {os.path.basename(event.src_path)}")
            # You can add custom logic here when files change

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.md'):
            print(f"New file detected: {os.path.basename(event.src_path)}")

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.endswith('.md'):
            print(f"File deleted: {os.path.basename(event.src_path)}")


def send_notification(title, message):
    """Send a system notification"""
    system = platform.system()

    try:
        if system == 'Darwin':  # macOS
            os.system(
                f"""osascript -e 'display notification "{message}" with title "{title}"'""")
        elif system == 'Linux':
            os.system(f'notify-send "{title}" "{message}"')
        elif system == 'Windows':
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=5)
        print(f"\n⏰ REMINDER: {title} - {message}")
    except Exception as e:
        print(f"Failed to send notification: {e}")
        print(f"\n⏰ REMINDER: {title} - {message}")


def reminder_thread(task_manager):
    """Background thread to check for due tasks"""
    while True:
        due_tasks = task_manager.get_due_tasks()
        for task in due_tasks:
            title = task.get('title', 'Untitled Task')
            due_time = task.get('due', 'Unknown')
            notes = task.get('notes', 'No additional notes')

            # Send notification
            send_notification(
                f"Task Due: {title}",
                f"Due at: {due_time}\n{notes[:50]}..."
            )

            # Print detailed task info
            print("\n" + "=" * 60)
            print(f"⏰ TASK DUE: {title}")
            print("-" * 60)
            print(f"Due: {due_time}")
            print(f"Status: {task.get('status', 'pending')}")
            print(f"Created: {task.get('created', 'Unknown')}")
            print("\nNotes:")
            print(notes)
            print("=" * 60)

            # Sleep to avoid repeated notifications for the same task
            time.sleep(1)

        # Check every minute
        time.sleep(60)


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python obsidian_tasks.py <obsidian_base_dir> [command] [args]")
        print("\nCommands:")
        print("  create <title> [due_date]    - Create a new task")
        print(
            "  list [status]                - List all tasks, optionally filtered by status")
        print("  complete <task_name>         - Mark a task as complete")
        print("  delete <task_name>           - Delete a task")
        print("  watch                        - Start monitoring task files for changes")
        print("  remind                       - Start reminder daemon for due tasks")
        sys.exit(1)

    base_dir = sys.argv[1]
    task_manager = ObsidianTaskManager(base_dir)

    if len(sys.argv) < 3:
        # Default to list if no command specified
        task_manager.list_tasks()
        return

    command = sys.argv[2]

    if command == "create":
        if len(sys.argv) < 4:
            print("Missing task title")
            return
        title = sys.argv[3]
        due_date = sys.argv[4] if len(sys.argv) > 4 else None
        task_manager.create_task(title, due_date)

    elif command == "list":
        status = sys.argv[3] if len(sys.argv) > 3 else None
        task_manager.list_tasks(status)

    elif command == "complete":
        if len(sys.argv) < 4:
            print("Missing task name")
            return
        task_manager.complete_task(sys.argv[3])

    elif command == "delete":
        if len(sys.argv) < 4:
            print("Missing task name")
            return
        task_manager.delete_task(sys.argv[3])

    elif command == "watch":
        print(f"Monitoring task directory: {task_manager.task_dir}")
        event_handler = TaskWatcher(task_manager)
        observer = Observer()
        observer.schedule(
            event_handler, task_manager.task_dir, recursive=False)
        observer.start()

        # Also start reminder thread
        reminder = threading.Thread(
            target=reminder_thread, args=(task_manager,), daemon=True)
        reminder.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    elif command == "remind":
        print("Starting reminder daemon for due tasks...")
        reminder_thread(task_manager)

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
