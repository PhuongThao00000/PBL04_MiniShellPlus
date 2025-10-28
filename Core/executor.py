import subprocess, sys, shutil, os
from Core.process_monitor.monitor import job_manager
from Core.utils import build_popen_args


def run_external(args, stdin=None, stdout=None):
    if shutil.which(args[0]) is None:
        print(f"minishell: command not found: {args[0]}")
        return None

    # Thiết lập các tham số Popen
    popen_kwargs = {
        "stdin": stdin,
        "stdout": stdout,
        "stderr": subprocess.PIPE,
    }

    popen_kwargs["preexec_fn"] = os.setpgrp

    try:
        return subprocess.Popen(args, **popen_kwargs)
    except Exception as e:
        print(f"Error running external command: {e}")
        return None


def execute_pipeline(cmds, background=False):
    procs, opened_files = [], []
    prev_stdout = None
    cmd_string = " | ".join(cmds)

    for idx, cmd_str in enumerate(cmds):
        args, stdin_f, stdout_f = build_popen_args(cmd_str)
        stdin = stdin_f or prev_stdout
        stdout = stdout_f or (subprocess.PIPE if idx < len(cmds) - 1 else None)
        p = run_external(args, stdin=stdin, stdout=stdout)
        if not p: return
        procs.append(p)
        if prev_stdout: prev_stdout.close()
        prev_stdout = p.stdout
        if stdin_f: opened_files.append(stdin_f)
        if stdout_f: opened_files.append(stdout_f)

    if background:
        job = job_manager.register_job(procs[-1], cmd_string)
        if job:
            print(f"[{job.jid}] {job.pid}")
        return

    for p in procs[:-1]:
        p.wait()
    if procs:
        try:
            out, err = procs[-1].communicate()
            if out: sys.stdout.buffer.write(out)
            if err: sys.stderr.buffer.write(err)
        except KeyboardInterrupt:
            print()
            import signal
            procs[-1].send_signal(signal.SIGINT)

    for f in opened_files: f.close()