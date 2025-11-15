import os
import signal
import psutil

# Background jobs: pid → command string
background_jobs = {}


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


def init_signal_handlers():
    """Khởi tạo signal handlers"""
    signal.signal(signal.SIGCHLD, handle_sigchld)


def add_background_job(pid, cmdline):
    """Thêm job vào danh sách background"""
    background_jobs[pid] = cmdline
    print(f"[{pid}] started in background: {cmdline}")


def show_jobs():
    """Hiển thị danh sách tiến trình nền"""
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


def cleanup_jobs():
    """Cleanup tất cả background jobs khi thoát"""
    for pid in list(background_jobs.keys()):
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Terminated background job [{pid}]")
        except ProcessLookupError:
            pass
        except Exception as e:
            print(f"Could not terminate job {pid}: {e}")