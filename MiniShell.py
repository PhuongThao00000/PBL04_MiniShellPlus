#!/usr/bin/env python3
"""
MiniShell – Python 3
Features:
 - Builtins: cd, exit, help, history, pmon
 - External commands via subprocess
 - Pipes (a | b | c)
 - I/O redirection: >, >>, <
 - Background execution with trailing &
 - Command history (readline)
 - Ctrl+C handling (không thoát shell)
 - Hỗ trợ sudo: hỏi mật khẩu và chạy lệnh với quyền root
"""

import os
import pty
import shlex
import shutil
import subprocess
import sys
import signal
import time
import getpass

import psutil

# ---------- History ----------
try:
    import readline
except ImportError:  # fallback cho Windows
    import pyreadline as readline

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


# ---------- Built-in commands ----------
def builtin_help():
    print("""MiniShell help:
 Built-in commands:
  cd [dir]      : change directory
  exit          : exit shell
  help          : print this help
  history       : show command history
  pmon          : process monitor
Features:
  Pipes using |
  Redirection using > >> <
  Background with & (run command in background)
  sudo <cmd>    : run command with root privileges
""")


def builtin_history():
    hlen = readline.get_current_history_length()
    for i in range(1, hlen + 1):
        print(f"{i}\t{readline.get_history_item(i)}")


def run_with_sudo(command):
    """
    Hỏi mật khẩu và chạy lệnh sudo trong pseudo-terminal
    """
    password = getpass.getpass("sudo password: ")
    master, slave = pty.openpty()
    p = subprocess.Popen(
        ["sudo", "-S"] + command,
        stdin=master,
        stdout=sys.stdout,
        stderr=sys.stderr,
        universal_newlines=True
    )
    os.write(master, (password + "\n").encode())
    p.wait()
    os.close(master)
    os.close(slave)


def builtin_pmon(interval=1.5, top_n=20):
    """Simple process monitor using psutil. Press Ctrl+C to return to shell."""
    try:
        while True:
            os.system("clear")
            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    cpu = p.info["cpu_percent"] or p.cpu_percent(interval=0)
                    procs.append((p.info["pid"], p.info["name"] or "?", cpu, p.info["memory_percent"] or 0.0))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            procs.sort(key=lambda x: x[2], reverse=True)
            print(f"{'PID':<8} {'Name':<28} {'CPU%':>6} {'MEM%':>6}")
            print("-" * 55)
            for pid, name, cpu, mem in procs[:top_n]:
                print(f"{pid:<8} {name[:26]:<28} {cpu:6.2f} {mem:6.2f}")
            print(f"\nPress Ctrl+C to return. Refresh: {interval}s")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nReturning to shell...")


# ---------- Signal ----------
def handle_sigint(signum, frame):
    # Ctrl+C tại prompt chỉ xuống dòng, không thoát shell
    print()


signal.signal(signal.SIGINT, handle_sigint)


# ---------- Parsing ----------
def parse_command(line):
    """
    Return list of pipeline segments and background flag.
    """
    line = line.strip()
    if not line:
        return [], False

    background = line.endswith("&")
    if background:
        line = line[:-1].strip()

    lex = shlex.shlex(line, posix=True)
    lex.whitespace_split = True
    lex.commenters = ""
    tokens = list(lex)

    segments, cur = [], []
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
    Parse redirections. Return (args, stdin_f, stdout_f)
    """
    tokens = shlex.split(cmd_str, posix=True)
    args, stdin_f, stdout_f = [], None, None
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        try:
            if tok == "<":
                stdin_f = open(os.path.expanduser(tokens[i + 1]), "rb")
                i += 2
            elif tok == ">":
                stdout_f = open(os.path.expanduser(tokens[i + 1]), "wb")
                i += 2
            elif tok == ">>":
                stdout_f = open(os.path.expanduser(tokens[i + 1]), "ab")
                i += 2
            else:
                args.append(tok)
                i += 1
        except (IndexError, OSError) as e:
            print(f"minishell: redirection error: {e}")
            return None, None, None
    return args, stdin_f, stdout_f


# ---------- External command ----------
def run_external(args, stdin=None, stdout=None):
    """
    Chạy lệnh ngoài:
      * Nếu không tìm thấy: gợi ý apt install (Ubuntu/Debian)
      * Nếu có: chạy subprocess
    """
    try:
        if shutil.which(args[0]) is None:
            try:
                res = subprocess.run(
                    ["apt-cache", "search", f"^{args[0]}$"],
                    capture_output=True, text=True
                )
                if res.stdout.strip():
                    print(f"minishell: command '{args[0]}' not found. Install with:")
                    print(f"  sudo apt install {args[0]}")
                else:
                    print(f"minishell: command '{args[0]}' not found. Maybe the text is wrong. Please try again.")
            except FileNotFoundError:
                print(f"minishell: command '{args[0]}' not found.")
            return None

        return subprocess.Popen(
            args,
            stdin=stdin,
            stdout=stdout,
            stderr=subprocess.PIPE,
            preexec_fn=os.setpgrp
        )
    except Exception as e:
        print(f"minishell: failed to execute '{args[0]}': {e}")
        return None


# ---------- Pipeline executor ----------
def execute_pipeline(cmds, background=False):
    procs, opened_files = [], []
    prev_stdout = None

    try:
        for idx, cmd_str in enumerate(cmds):
            args, stdin_f, stdout_f = build_popen_args(cmd_str)
            if not args:
                break

            stdin = stdin_f if idx == 0 and stdin_f else prev_stdout
            stdout = (
                stdout_f if idx == len(cmds) - 1 and stdout_f
                else subprocess.PIPE if idx < len(cmds) - 1
                else None
            )

            if stdin_f: opened_files.append(stdin_f)
            if stdout_f: opened_files.append(stdout_f)

            p = run_external(args, stdin=stdin, stdout=stdout)
            if not p:
                break
            procs.append(p)

            if prev_stdout and prev_stdout is not sys.stdin:
                try: prev_stdout.close()
                except Exception: pass
            prev_stdout = p.stdout

        if background and procs:
            print(f"[{procs[-1].pid}] started in background")
            return

        for p in procs[:-1]:
            p.wait()
        if procs:
            out, err = procs[-1].communicate()
            if err:
                sys.stderr.write(err.decode(errors="ignore"))

    finally:
        for f in opened_files:
            try: f.close()
            except Exception: pass


# ---------- Prompt & main loop ----------
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
                line = input(prompt()).strip()
            except EOFError:
                print()
                break
            if not line:
                continue

            # ---- Built-in ----
            if line.startswith("sudo "):
                parts = shlex.split(line)
                if len(parts) > 1:
                    run_with_sudo(parts[1:])
                else:
                    print("Usage: sudo <command>")
                continue

            if line.startswith("cd "):
                path = line[3:].strip() or os.path.expanduser("~")
                try:
                    os.chdir(os.path.expanduser(path))
                except Exception as e:
                    print(f"cd: {e}")
                continue
            if line == "exit":
                break
            if line == "help":
                builtin_help()
                continue
            if line == "history":
                builtin_history()
                continue
            if line.startswith("pmon"):
                builtin_pmon()
                continue

            # ---- External / pipeline ----
            cmds, background = parse_command(line)
            if cmds:
                execute_pipeline(cmds, background)
    finally:
        save_history()


if __name__ == "__main__":
    main_loop()
