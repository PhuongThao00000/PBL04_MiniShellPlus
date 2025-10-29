import subprocess, sys, shutil, os
from Core.process import bg_jobs
from Core.utils import build_popen_args

def run_external(args, stdin=None, stdout=None):
    if shutil.which(args[0]) is None:
        print(f"minishell: command not found: {args[0]}")
        return None
    return subprocess.Popen(args, stdin=stdin, stdout=stdout,
                            stderr=subprocess.PIPE, preexec_fn=os.setpgrp)

def execute_pipeline(cmds, background=False):
    procs, opened_files = [], []
    prev_stdout = None

    for idx, cmd_str in enumerate(cmds):
        args, stdin_f, stdout_f = build_popen_args(cmd_str)
        stdin = stdin_f or prev_stdout
        stdout = stdout_f or (subprocess.PIPE if idx < len(cmds)-1 else None)
        p = run_external(args, stdin=stdin, stdout=stdout)
        if not p: return
        procs.append(p)
        if prev_stdout: prev_stdout.close()
        prev_stdout = p.stdout
        if stdin_f: opened_files.append(stdin_f)
        if stdout_f: opened_files.append(stdout_f)

    if background:
        bg_jobs(procs[-1].pid, " | ".join(cmds))
        return

    for p in procs[:-1]:
        p.wait()
    if procs:
        out, err = procs[-1].communicate()
        if out: sys.stdout.buffer.write(out)
        if err: sys.stderr.buffer.write(err)

    for f in opened_files: f.close()
