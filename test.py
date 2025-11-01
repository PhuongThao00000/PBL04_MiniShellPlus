
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
"""

import os
import shlex
import shutil
import subprocess
import sys
import signal
import time
import psutil

# ---------- History ----------
try:
    import readline
except ImportError:  # fallback cho Windows
    import pyreadline as readline

HISTORY_FILE = os.path.expanduser("~/.minishell_history")
MAX_HISTORY = 1000  # Giới hạn số lệnh lưu
last_status = 0


def init_readline():
    """Cấu hình readline để hoạt động giống terminal Linux"""
    try:
        # Kiểm tra xem có đang chạy trong terminal thật không
        if not sys.stdin.isatty():
            print("Warning: Not running in a real terminal. History navigation may not work properly.")
            print("Please run this script in a real terminal instead of IDE console.")
            return

        # Kích hoạt tìm kiếm history với Ctrl+R
        readline.parse_and_bind("tab: complete")

        # Phím mũi tên lên/xuống để duyệt history (mặc định có sẵn)
        # Nhưng có thể cấu hình thêm:
        readline.parse_and_bind("\\e[A: previous-history")  # Mũi tên lên
        readline.parse_and_bind("\\e[B: next-history")  # Mũi tên xuống

        # Ctrl+Left/Right để nhảy giữa các từ
        readline.parse_and_bind("\\e[1;5D: backward-word")  # Ctrl+Left
        readline.parse_and_bind("\\e[1;5C: forward-word")  # Ctrl+Right

        # Emacs key bindings (giống bash)
        readline.parse_and_bind("set editing-mode emacs")

        # Tự động complete không phân biệt hoa/thường
        readline.parse_and_bind("set completion-ignore-case on")

        # Hiển thị tất cả matches nếu nhiều hơn 1
        readline.parse_and_bind("set show-all-if-ambiguous on")

    except Exception as e:
        print(f"Warning: Could not configure readline: {e}", file=sys.stderr)


def save_history():
    try:
        readline.set_history_length(MAX_HISTORY)
        readline.write_history_file(HISTORY_FILE)
    except Exception as e:
        print(f"Warning: Could not save history: {e}", file=sys.stderr)


def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            readline.read_history_file(HISTORY_FILE)
            readline.set_history_length(MAX_HISTORY)
    except Exception as e:
        print(f"Warning: Could not load history: {e}", file=sys.stderr)


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

# --- Process Management ---
background_jobs = {}  # pid → command string
def handle_sigchld(signum, frame):
    """Dọn zombie và thông báo khi tiến trình nền kết thúc"""
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break
            if pid in background_jobs:
                print(f"\n[{pid}] finished: {background_jobs.pop(pid)}")
        except ChildProcessError:
            break
        except Exception:
            break

signal.signal(signal.SIGCHLD, handle_sigchld) #in message trong handle_sigchld() thong bao khi xong

def builtin_history():
    hlen = readline.get_current_history_length()
    for i in range(1, hlen + 1):
        print(f"{i}\t{readline.get_history_item(i)}")

def builtin_pmon():
    """Hiển thị danh sách tiến trình nền đang chạy"""
    if not background_jobs:
        print("No background jobs.")
        return
    print(f"{'PID':<8} {'Command'}")
    print("-" * 40)
    for pid, cmd in background_jobs.items():
        try:
            if psutil.pid_exists(pid):
                p = psutil.Process(pid)
                status = p.status()
                print(f"{pid:<8} {cmd}  [{status}]")
            else:
                print(f"{pid:<8} {cmd}  [terminated]")
        except Exception:
            print(f"{pid:<8} {cmd}  [unknown]")


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
      - Nếu không tìm thấy: gợi ý apt install
      - Nếu có: chạy subprocess với nhóm tiến trình riêng
    """
    try:
        if shutil.which(args[0]) is None:
            try:
                res = subprocess.run(
                    ["apt-cache", "search", f"^{args[0]}$"],
                    capture_output=True, text=True
                )
                last_status = res.returncode
                if res.stdout.strip():
                    print(f"minishell: command '{args[0]}' not found. Install with:")
                    print(f"  sudo apt install {args[0]}")
                else:
                    print(f"minishell: command '{args[0]}' not found. Maybe the text is wrong.")
            except FileNotFoundError:
                print(f"minishell: command '{args[0]}' not found.")
            return None

        # preexec_fn=os.setpgrp giúp tách process group → Ctrl+C không kill shell
        return subprocess.Popen(
            args,
            stdin=stdin,
            stdout=stdout,
            stderr=subprocess.PIPE,
            preexec_fn=os.setpgrp
        )
    except PermissionError:
        print(f"minishell: permission denied: {args[0]}")
        return None
    except FileNotFoundError:
        print(f"minishell: command not found: {args[0]}")
        return None
    except Exception as e:
        print(f"minishell: failed to execute '{args[0]}': {e}")
        return None


# ---------- Pipeline executor ----------
# ---------- Pipeline executor ----------
def execute_pipeline(cmds, background=False):
    global last_status
    procs, opened_files = [], []
    prev_stdout = None

    try:
        for idx, cmd_str in enumerate(cmds):
            args, stdin_f, stdout_f = build_popen_args(cmd_str)
            if not args:
                last_status = 1
                break

            stdin = stdin_f if idx == 0 and stdin_f else prev_stdout
            stdout = (
                stdout_f if idx == len(cmds) - 1 and stdout_f
                else subprocess.PIPE if idx < len(cmds) - 1
                else None
            )

            if stdin_f:
                opened_files.append(stdin_f)
            if stdout_f:
                opened_files.append(stdout_f)

            p = run_external(args, stdin=stdin, stdout=stdout)
            if not p:
                last_status = 127  # Command not found
                return
            procs.append(p)

            if prev_stdout and prev_stdout is not sys.stdin:
                try:
                    prev_stdout.close()
                except Exception:
                    pass
            prev_stdout = p.stdout

        # ---- Background ----
        if background and procs:
            cmdline = " | ".join(cmds)
            background_jobs[procs[-1].pid] = cmdline
            print(f"[{procs[-1].pid}] started in background: {cmdline}")
            last_status = 0
            return

        # ---- Foreground ----
        exit_code = 0
        for p in procs[:-1]:
            p.wait()

        if procs:
            out, err = procs[-1].communicate()
            exit_code = procs[-1].returncode

            if out:
                sys.stdout.buffer.write(out)
            if err:
                sys.stderr.buffer.write(err)

        last_status = exit_code  # cập nhật mã thoát cuối cùng

        if exit_code != 0:
            print(f"minishell: process exited with code {exit_code}")

    finally:
        for f in opened_files:
            try:
                f.close()
            except Exception:
                pass

# ---------- Prompt & main loop ----------
def prompt():
    user = os.getenv("USER") or os.getenv("USERNAME") or "user"
    cwd = os.getcwd()
    base = os.path.basename(cwd) or "/"
    return f"{user}@minishell:{base}$ "


def main_loop():
    global last_status
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
                print("", flush=True)
                continue

            if not line:
                continue

            # Thay thế biến $? trước khi chạy
            if "$?" in line:
                line = line.replace("$?", str(last_status))

            readline.add_history(line)

            # ---- Builtins ----
            if line.startswith("cd"):
                path = line[3:].strip() or os.path.expanduser("~")
                try:
                    os.chdir(os.path.expanduser(path))
                    last_status = 0
                except Exception as e:
                    print(f"cd: {e}")
                    last_status = 1
                continue

            if line == "exit":
                last_status = 0
                break

            if line == "help":
                builtin_help()
                last_status = 0
                continue

            if line == "history":
                builtin_history()
                last_status = 0
                continue

            if line == "pmon":
                builtin_pmon()
                last_status = 0
                continue

            # ---- External / Pipeline ----
            cmds, background = parse_command(line)
            if cmds:
                execute_pipeline(cmds, background)

    finally:
        try:
            save_history()
        except Exception as e:
            print(f"Warning: Could not save history: {e}", file=sys.stderr)

        # ---- Cleanup background jobs ----
        for pid in list(background_jobs.keys()):
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Terminated background job [{pid}]")
            except ProcessLookupError:
                pass
            except Exception as e:
                print(f"Could not terminate job {pid}: {e}")
        print("Goodbye!")

if __name__ == "__main__":
    main_loop()