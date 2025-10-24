# pmon.py
# file quan ly cac tien trinh chay nen cho MiniShell Plus

import os
import signal
import psutil

from Core.prompt import get_prompt

# luu cac tien trinh chay nen dang hoat dong
bg_jobs = {}

# ham xu ly khi 1 tien trinh con ket thuc
def sigchld_handler(sig, frame):
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break
            if pid in bg_jobs:
                print(f"\n[{pid}] done: {bg_jobs.pop(pid)}")
        except ChildProcessError:
            break

# dang ky tin hieu SIGCHLD
signal.signal(signal.SIGCHLD, sigchld_handler)


# them tien trinh vao danh sach chay nen
def add_bg(pid, cmd):
    bg_jobs[pid] = cmd
    print(f"[{pid}] running in background: {cmd}")


# hien thi danh sach tien trinh chay nen
def show_pmon():
    if not bg_jobs:
        print("Khong co tien trinh nen nao ca.")
        return
    print(f"{'PID':<8}{'Lenh':<25}{'Trang thai'}")
    for pid, cmd in bg_jobs.items():
        if psutil.pid_exists(pid):
            try:
                p = psutil.Process(pid)
                status = p.status()
            except Exception:
                status = "unknown"
        else:
            status = "terminated"
        print(f"{pid:<8}{cmd:<25}{status}")


# dung tat ca tien trinh chay nen khi thoat shell
def cleanup_bg():
    for pid in list(bg_jobs.keys()):
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Da dung tien trinh [{pid}]")
        except:
            pass

