import os
import sys
from config import HISTORY_FILE, MAX_HISTORY

try:
    import readline
except ImportError:
    import pyreadline as readline


def init_readline():
    """Cấu hình readline để hoạt động giống terminal Linux"""
    try:
        if not sys.stdin.isatty():
            print("Warning: Not running in a real terminal. History navigation may not work properly.")
            print("Please run this script in a real terminal instead of IDE console.")
            return

        # Kích hoạt tìm kiếm history với Ctrl+R
        readline.parse_and_bind("tab: complete")

        # Phím mũi tên lên/xuống
        readline.parse_and_bind("\\e[A: previous-history")
        readline.parse_and_bind("\\e[B: next-history")

        # Ctrl+Left/Right để nhảy giữa các từ
        readline.parse_and_bind("\\e[1;5D: backward-word")
        readline.parse_and_bind("\\e[1;5C: forward-word")

        # Emacs key bindings
        readline.parse_and_bind("set editing-mode emacs")

        # Case-insensitive completion
        readline.parse_and_bind("set completion-ignore-case on")
        readline.parse_and_bind("set show-all-if-ambiguous on")

    except Exception as e:
        print(f"Warning: Could not configure readline: {e}", file=sys.stderr)


def save_history():
    """Lưu history ra file"""
    try:
        readline.set_history_length(MAX_HISTORY)
        readline.write_history_file(HISTORY_FILE)
    except Exception as e:
        print(f"Warning: Could not save history: {e}", file=sys.stderr)


def load_history():
    """Load history từ file"""
    try:
        if os.path.exists(HISTORY_FILE):
            readline.read_history_file(HISTORY_FILE)
            readline.set_history_length(MAX_HISTORY)
    except Exception as e:
        print(f"Warning: Could not load history: {e}", file=sys.stderr)


def add_to_history(line):
    """Thêm command vào history"""
    readline.add_history(line)


def show_history():
    """In ra toàn bộ history"""
    hlen = readline.get_current_history_length()
    for i in range(1, hlen + 1):
        print(f"{i}\t{readline.get_history_item(i)}")