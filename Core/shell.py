import os
import sys
import re
from Core.history import init_readline, load_history, save_history
from Core.job_control import init_signal_handlers, cleanup_jobs
from Core.builtin import execute_builtin, expand_alias
from Core.parser import parse_command
from Core.executor import execute_pipeline

# Global state
last_status = 0


def prompt():
    """Generate shell prompt"""
    user = os.getenv("USER") or os.getenv("USERNAME") or "user"
    cwd = os.getcwd()
    base = os.path.basename(cwd) or "/"
    return f"{user}@minishell:{base}$ "

def expand_variables(line):
    """
    Thay thế biến môi trường trong command line.
    Hỗ trợ: $VAR, ${VAR}, $?
    """
    # Thay thế $? (exit status)
    line = line.replace("$?", str(last_status))

    # Thay thế ${VAR}
    line = re.sub(r'\$\{(\w+)\}', lambda m: os.getenv(m.group(1), ''), line)

    # Thay thế $VAR
    line = re.sub(r'\$(\w+)', lambda m: os.getenv(m.group(1), ''), line)

    return line
def main_loop():
    """Main shell loop"""
    global last_status

    # Setup
    init_signal_handlers()
    init_readline()
    load_history()

    try:
        while True:
            try:
                line = input(prompt()).strip()
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                continue

            if not line:
                continue

            line = expand_variables(line)

            # Check for exit
            if line == "exit":
                last_status = 0
                break

            # Expand alias trước khi chạy
            line = expand_alias(line)

            # Try built-in commands
            executed, exit_code = execute_builtin(line)
            if executed:
                last_status = exit_code
                continue

            # Parse and execute pipeline
            cmds, background = parse_command(line)
            if cmds:
                last_status = execute_pipeline(cmds, background)

    finally:
        try:
            save_history()
        except Exception as e:
            print(f"Warning: Could not save history: {e}", file=sys.stderr)

        cleanup_jobs()
        print("Goodbye!")