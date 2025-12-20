import os
import sys
import re
import shlex
from Core.history import init_readline, load_history, save_history
from Core.job_control import init_signal_handlers, cleanup_jobs
from Core.builtin import execute_builtin, expand_alias
from Core.parser import parse_command
from Core.executor import execute_pipeline

# Global state
last_status = 0


def prompt():
    """Generate shell prompt"""
    cwd = os.getcwd()
    base = os.path.basename(cwd) or "/"

    GREEN = "\033[92m"
    RESET = "\033[0m"

    return f"{GREEN}minishell:{base}$ {RESET}"


def continuation_prompt():
    """Generate continuation prompt for multi-line input"""
    return "> "


def expand_variables(line):
    """
    Thay thế biến môi trường trong command line.
    Hỗ trợ: $VAR, ${VAR}, $?
    """
    # Thay thế $? (exit status)
    line = line.replace("$?", str(last_status))

    # Thay thế ${VAR}
    line = re.sub(r'\$\{(\w+)\}', lambda m: os.getenv(m.group(1), ''), line)

    # Thay thế $VAR (không bắt đầu bằng số)
    line = re.sub(r'\$([a-zA-Z_]\w*)', lambda m: os.getenv(m.group(1), ''), line)

    return line


def is_incomplete_command(line):
    """
    Kiểm tra xem command có hoàn chỉnh không (quote đã đóng chưa)
    Returns: True nếu chưa hoàn chỉnh (cần nhập tiếp)
    """
    try:
        # Thử parse với shlex
        shlex.split(line)
        return False
    except ValueError:
        # Nếu có lỗi parse -> quote chưa đóng
        return True


def read_multiline_command():
    """
    Đọc command, hỗ trợ multi-line nếu quote chưa đóng
    Returns: complete command string hoặc None nếu EOF/Interrupt
    """
    try:
        line = input(prompt()).strip()
    except EOFError:
        return None
    except KeyboardInterrupt:
        print()
        return ""

    # Kiểm tra nếu command chưa hoàn chỉnh (quote chưa đóng)
    while is_incomplete_command(line):
        try:
            # Nhập tiếp với prompt ">"
            continuation = input(continuation_prompt())
            line += "\n" + continuation
        except EOFError:
            print("\nminishell: syntax error: unexpected end of file")
            return ""
        except KeyboardInterrupt:
            print("\nminishell: syntax error: command interrupted")
            return ""

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
            # Đọc command (hỗ trợ multi-line)
            line = read_multiline_command()

            # Xử lý EOF
            if line is None:
                print()
                break

            # Skip empty lines
            if not line:
                continue

            # Expand variables
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