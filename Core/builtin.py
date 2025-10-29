import os
from Core.history import show_history
from Core.process import show_pmon

def handle_builtin(line):
    parts = line.split()
    if not parts: return False
    cmd = parts[0]
    if cmd == "exit":
        exit(0)
    elif cmd == "cd":
        path = parts[1] if len(parts) > 1 else os.path.expanduser("~")
        try: os.chdir(path)
        except Exception as e: print(f"cd: {e}")
        return True
    elif cmd == "help":
        print("Built-ins: cd, exit, help, history, pmon")
        return True
    elif cmd == "history":
        show_history()
        return True
    elif cmd == "pmon":
        show_pmon()
        return True
    return False
