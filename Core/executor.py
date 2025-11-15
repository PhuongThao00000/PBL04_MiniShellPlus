import os
import sys
import shutil
import subprocess
from Core.parser import build_popen_args
from Core.job_control import add_background_job


def run_external(args, stdin=None, stdout=None, interactive=False):
    """
    Chạy lệnh ngoài với subprocess.
    Returns: Popen object or None
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
                    print(f"minishell: command '{args[0]}' not found. Maybe the text is wrong.")
            except FileNotFoundError:
                print(f"minishell: command '{args[0]}' not found.")
            return None

        # Nếu là chương trình interactive (không có pipe/redirect),
        # KHÔNG dùng preexec_fn để giữ terminal control
        if interactive:
            return subprocess.Popen(
                args,
                stdin=stdin,
                stdout=stdout,
                stderr=subprocess.PIPE
            )
        else:
            # preexec_fn=os.setpgrp giúp tách process group cho background jobs
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


def execute_pipeline(cmds, background=False):
    """
    Execute pipeline of commands.
    Returns: exit_code
    """
    procs, opened_files = [], []
    prev_stdout = None

    # Detect nếu là single command không có pipe/redirect -> interactive mode
    interactive = (len(cmds) == 1 and '>' not in cmds[0] and '<' not in cmds[0])

    try:
        for idx, cmd_str in enumerate(cmds):
            args, stdin_f, stdout_f = build_popen_args(cmd_str)
            if not args:
                return 1

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

            # Interactive mode cho single command
            is_interactive = interactive and idx == 0 and not stdin_f and not stdout_f

            p = run_external(args, stdin=stdin, stdout=stdout, interactive=is_interactive)
            if not p:
                return 127  # Command not found

            procs.append(p)

            if prev_stdout and prev_stdout is not sys.stdin:
                try:
                    prev_stdout.close()
                except Exception:
                    pass
            prev_stdout = p.stdout

        # Background execution
        if background and procs:
            cmdline = " | ".join(cmds)
            add_background_job(procs[-1].pid, cmdline)
            return 0

        # Foreground execution
        exit_code = 0

        if interactive and procs:
            # Interactive mode: wait trực tiếp không capture output
            exit_code = procs[-1].wait()
        else:
            # Pipeline mode: capture output như cũ
            for p in procs[:-1]:
                p.wait()

            if procs:
                out, err = procs[-1].communicate()
                exit_code = procs[-1].returncode

                if out:
                    sys.stdout.buffer.write(out)
                if err:
                    sys.stderr.buffer.write(err)

        if exit_code != 0:
            print(f"minishell: process exited with code {exit_code}")

        return exit_code

    finally:
        for f in opened_files:
            try:
                f.close()
            except Exception:
                pass