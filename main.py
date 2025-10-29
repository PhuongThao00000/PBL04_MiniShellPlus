from Core.prompt import get_prompt
from Core.parser import parse_command
from Core.executor import execute_pipeline
from Core.builtin import handle_builtin
from Core.history import init_history, save_history, load_history
from Core.process import cleanup_bg

import signal

def main():
    init_history()
    load_history()

    try:
        while True:
            try:
                line = input(get_prompt())
            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                continue

            if not line.strip():
                continue

            # Built-ins
            if handle_builtin(line):
                continue

            # External / Pipeline
            cmds, background = parse_command(line)
            execute_pipeline(cmds, background)
    finally:
        save_history()
        cleanup_bg()

if __name__ == "__main__":
    main()
