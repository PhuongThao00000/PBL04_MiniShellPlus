#!/usr/bin/env python3
"""
MiniShell - Python
Features:
 - Builtins: cd, exit, help, history, pmon
 - External commands via subprocess
 - Pipes (a | b | c)
 - I/O redirection: >, >>, <
 - Background execution with trailing &
 - Command history (readline)
 - Ctrl+C handling (does not kill the shell)
"""

import os #Thu vien chuan giup thao tac voi he dieu hanh
import shlex #dung de tach chuoi dong lenh, "python3 my script.py"->['python3','my','script.py']-> useful if user enter have space,dau nhay
import shutil #Kiem tra, xu li tep va thu muc
import subprocess #thu vien dung de chay cac lenh he thong tu python
import sys #Tuong tac voi trinh thong dich
try:
    import readline #Tao lich su dong lenh
except ImportError:
    import pyreadline as readline #neu 0 co san thi dung pyreadline thay the

import signal #bat tin hieu he thong. Dung lenh, nhung k thoat shell: Ctrl + C
import psutil #theo doi tien trinh he thong
import time #cho doi, hen lap h

# -----------------------------
# Utilities / Builtins
# -----------------------------

HISTORY_FILE = os.path.expanduser("~/.minishell_history")

def save_history():
    try:
        readline.write_history_file(HISTORY_FILE)
    except Exception:
        pass

def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            readline.read_history_file(HISTORY_FILE)
    except Exception:
        pass

def builtin_help():
    print("""MiniShell help:
 Built-in commands:
  - cd [dir]       : change directory
  - exit           : exit shell
  - help           : print this help
  - history        : show command history
  - pmon           : show process monitor (press Ctrl+C to stop)
 Features:
  - Pipes using |
  - Redirection using > >> <
  - Background with & (run command in background)
""")

def builtin_history():
    hlen = readline.get_current_history_length()
    for i in range(1, hlen + 1):
        print(f"{i}\t{readline.get_history_item(i)}")

def builtin_pmon(interval=1.5, top_n=20):
    """Simple process monitor using psutil. Press Ctrl+C to return to shell."""
    try:
        while True:
            os.system('clear')
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    # call cpu_percent once to get updated value
                    cpu = p.info['cpu_percent']
                    if cpu is None:
                        cpu = p.cpu_percent(interval=0)
                    procs.append((p.info['pid'], p.info['name'] or "?", cpu, p.info['memory_percent'] or 0.0))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            procs.sort(key=lambda x: x[2], reverse=True)
            print(f"{'PID':<8} {'Name':<30} {'CPU%':>6} {'MEM%':>6}")
            print("-" * 55)
            for pid, name, cpu, mem in procs[:top_n]:
                print(f"{pid:<8} {name[:28]:<30} {cpu:6.2f} {mem:6.2f}")
            print("\nPress Ctrl+C to return to shell. Updating every", interval, "s.")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nReturning to shell...")
        return

# -----------------------------
# Signal handling
# -----------------------------

# When user presses Ctrl+C in the shell prompt, we want to interrupt running children
# but not exit the shell itself. We'll handle KeyboardInterrupt in the main loop.
def handle_sigint(signum, frame):
    # noop here - KeyboardInterrupt will be raised in input/readline
    print("")  # newline to keep prompt tidy

signal.signal(signal.SIGINT, handle_sigint)

# -----------------------------
# Core Execution Helpers
# -----------------------------

def parse_command(line):
    """
    Returns:
      - cmds: list of command-strings split by '|'
      - background: bool whether command ends with &
    """
    line = line.strip()
    background = False
    if not line:
        return [], False

    if line.endswith("&"):
        background = True
        line = line[:-1].strip()

    # split respecting quotes (shlex)
    # but first split by pipes at top level.
    # Use shlex to do tokenization and then rebuild segments split by '|'
    lex = shlex.shlex(line, posix=True)
    lex.whitespace_split = True
    lex.commenters = ''
    tokens = list(lex)

    segments = []
    cur = []
    for tok in tokens:
        if tok == "|":
            segments.append(" ".join(cur))
            cur = []
        else:
            cur.append(tok)
    if cur:
        segments.append(" ".join(cur))

    return segments, background

def build_popen_args(cmd_str):
    """
    From a single command string (no pipes), parse redirections and return:
      - args (list) for exec
      - stdin (file object or None)
      - stdout (file object or None)
      - append (bool)
    """
    tokens = shlex.split(cmd_str, posix=True)
    args = []
    stdin = None
    stdout = None
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "<":
            if i + 1 < len(tokens):
                fname = os.path.expanduser(tokens[i+1])
                try:
                    stdin = open(fname, "rb")
                except Exception as e:
                    print(f"minishell: cannot open input file {fname}: {e}")
                    return None, None, None
                i += 2
            else:
                print("minishell: syntax error near unexpected token <")
                return None, None, None
        elif tok == ">":
            if i + 1 < len(tokens):
                fname = os.path.expanduser(tokens[i+1])
                try:
                    stdout = open(fname, "wb")
                except Exception as e:
                    print(f"minishell: cannot open output file {fname}: {e}")
                    return None, None, None
                i += 2
            else:
                print("minishell: syntax error near unexpected token >")
                return None, None, None
        elif tok == ">>":
            if i + 1 < len(tokens):
                fname = os.path.expanduser(tokens[i+1])
                try:
                    stdout = open(fname, "ab")
                except Exception as e:
                    print(f"minishell: cannot open output file {fname}: {e}")
                    return None, None, None
                i += 2
            else:
                print("minishell: syntax error near unexpected token >>")
                return None, None, None
        else:
            args.append(tok)
            i += 1

    return args, stdin, stdout

def execute_pipeline(cmds, background=False):
    """
    cmds: list of command-strings (already separated by pipe)
    background: whether to run in background
    """
    procs = []
    prev_stdout = None
    opened_files = []  # to close later

    try:
        for idx, cmd_str in enumerate(cmds):
            args, stdin_f, stdout_f = build_popen_args(cmd_str)
            if args is None:
                # parsing error (e.g. redirection file problem)
                # cleanup opened files
                for f in opened_files:
                    try: f.close()
                    except: pass
                return

            # First command: stdin possibly from '<'
            if idx == 0 and stdin_f:
                stdin = stdin_f
                opened_files.append(stdin_f)
            else:
                stdin = prev_stdout

            # Last command: stdout possibly to '>' or '>>'
            if idx == len(cmds) - 1 and stdout_f:
                stdout = stdout_f
                opened_files.append(stdout_f)
            else:
                stdout = subprocess.PIPE if idx < len(cmds) - 1 else None

            # Start process
            try:
                # preexec_fn=os.setpgrp to prevent child getting signals intended for shell (optional)
                p = subprocess.Popen(args, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE, preexec_fn=os.setpgrp)
            except FileNotFoundError:
                print(f"minishell: command {args[0]} not found, but can be installed with: ")

                # Gợi ý cài đặt (dành cho hệ Ubuntu/Debian)
                # Bạn có thể mở rộng theo OS khác nếu muốn
               # print(f"👉 Gợi ý: bạn có thể cài đặt nó bằng:")
                print(f"sudo apt install {args[0]}")

                # close opened files and any started procs
                for f in opened_files:
                    try: f.close()
                    except: pass
                for proc in procs:
                    try: proc.kill()
                    except: pass
                return
            except Exception as e:
                print(f"minishell: failed to execute {args[0]}: {e}")
                for f in opened_files:
                    try: f.close()
                    except: pass
                for proc in procs:
                    try: proc.kill()
                    except: pass
                return

            procs.append(p)

            # previous stdout becomes stdin for next
            if prev_stdout and prev_stdout is not sys.stdin:
                # close the previous stdout end in parent
                try:
                    prev_stdout.close()
                except:
                    pass
            prev_stdout = p.stdout

        if shutil.which(args[0]) is None:
            print(f"minishell: command not found: {args[0]}")
            print(f"👉 sudo apt install {args[0]}")
            return

        # If background: do not wait
        if background:
            print(f"[{procs[-1].pid}] started in background")
            # we do not call wait; leave the process running
            return

        # Foreground: wait for the last process; also print stderr if any
        # Optionally, wait for all children to finish
        for p in procs[:-1]:
            # wait for intermediate procs to avoid zombies
            p.wait()
        last = procs[-1]
        out, err = last.communicate()
        if err:
            # decode and print stderr
            try:
                msg = err.decode().strip()
                if msg:
                    print(msg, file=sys.stderr)
            except:
                pass

    finally:
        for f in opened_files:
            try:
                f.close()
            except:
                pass

# -----------------------------
# Shell loop
# -----------------------------

def prompt():
    user = os.getenv("USER") or os.getenv("USERNAME") or "user"
    cwd = os.getcwd()
    base = os.path.basename(cwd) or "/"
    return f"{user}@minishell:{base}$ "

def main_loop():
    load_history()
    try:
        while True:
            try:
                line = input(prompt())
            except EOFError:
                print("exit")
                break
            except KeyboardInterrupt:
                # Ctrl+C pressed at prompt: print newline and continue
                print("")
                continue

            line = line.strip()
            if not line:
                continue

            # Save to history
            readline.add_history(line)

            # Quick parse for builtins before heavy parsing:
            # We still need to handle pipe/redirection for non-builtin cases.
            if line == "help":
                builtin_help()
                continue
            if line == "history":
                builtin_history()
                continue
            if line.startswith("cd"):
                parts = shlex.split(line)
                if len(parts) == 1:
                    target = os.path.expanduser("~")
                else:
                    target = os.path.expanduser(parts[1])
                try:
                    os.chdir(target)
                except Exception as e:
                    print(f"cd: {e}")
                continue
            if line == "exit":
                break
            if line == "pmon":
                try:
                    builtin_pmon()
                except Exception as e:
                    print("pmon error:", e)
                continue

            # Otherwise parse pipeline + background
            cmds, background = parse_command(line)
            if not cmds:
                continue

            execute_pipeline(cmds, background=background)

    finally:
        save_history()
        print("Goodbye!")

if __name__ == "__main__":
    main_loop()