from Core.prompt import get_prompt
from Core.parser import parse_command
from Core.executor import execute_pipeline
from Core.builtin import handle_builtin
from Core.history import init_history, load_history, add_history, save_history_file
from Core.process_monitor.monitor import job_manager

import signal
import sys


def main():
    try:
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)
    except:
        pass

    init_history()
    load_history()

    try:
        while True:
            job_manager.update_all_statuses()

            try:
                line = input(get_prompt())
            except EOFError:
                print("exit")
                break
            except KeyboardInterrupt:
                print()
                continue

            if not line.strip():
                continue

            add_history(line)

            # Built-ins
            if handle_builtin(line):
                continue

            # External / Pipeline
            try:
                cmds, background = parse_command(line)
                execute_pipeline(cmds, background)
            except Exception as e:
                print(f"Execution error: {e}", file=sys.stderr)

    finally:
        save_history_file()
        print("\nMiniShell closing.")


if __name__ == "__main__":
    main()