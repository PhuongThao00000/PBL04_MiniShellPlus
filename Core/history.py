import os, sys
try:
    import readline
except ImportError:
    import pyreadline as readline

HISTORY_FILE = os.path.expanduser("~/.minishell_history")
MAX_HISTORY = 1000

def init_history():
    readline.parse_and_bind("tab: complete")
    readline.parse_and_bind("set editing-mode emacs")

def load_history():
    if os.path.exists(HISTORY_FILE):
        readline.read_history_file(HISTORY_FILE)
    readline.set_history_length(MAX_HISTORY)

def save_history():
    readline.write_history_file(HISTORY_FILE)

def show_history():
    for i in range(1, readline.get_current_history_length()+1):
        print(f"{i}\t{readline.get_history_item(i)}")
