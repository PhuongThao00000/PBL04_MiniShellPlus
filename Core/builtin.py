
import os
import signal
from Core.process_monitor.tui import start_tui
from Core.history import show_history
from Core.process_monitor.monitor import job_manager


def handle_builtin(line):
    parts = line.split()
    if not parts: return False
    cmd = parts[0]

    if cmd == "exit":
        exit(0)

    elif cmd == "cd":
        path = parts[1] if len(parts) > 1 else os.path.expanduser("~")
        try:
            os.chdir(path)
        except Exception as e:
            print(f"cd: {e}")
        return True

    elif cmd == "help":
        print("Built-ins: cd, exit, help, history, jobs, fg, bg, kill, pmon")
        return True

    elif cmd == "history":
        show_history()
        return True

    elif cmd == "jobs":
        job_list = job_manager.list_jobs()
        for job_str in job_list:
            print(job_str)
        return True

    elif cmd == "fg":
        if len(parts) < 2:
            print("fg: usage: fg <jid>")
        else:
            result = job_manager.bring_to_foreground(parts[1])
            if result: print(result)
        return True

    elif cmd == "bg":
        if len(parts) < 2:
            print("bg: usage: bg <jid>")
        else:
            result = job_manager.send_signal_to_job(parts[1], signal.SIGCONT)
            print(result)
        return True

    elif cmd == "kill":
        if len(parts) < 2:
            print("kill: usage: kill <jid>")
        else:
            result = job_manager.send_signal_to_job(parts[1], signal.SIGTERM)
            print(result)
        return True

    elif cmd == "pmon":
        start_tui()
        return True

    return False