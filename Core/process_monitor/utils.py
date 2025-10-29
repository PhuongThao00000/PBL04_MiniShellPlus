
import psutil
from . import log


def get_process_status(pid: int) -> str:

    if pid is None:
        return "Completed"

    try:
        p = psutil.Process(pid)
        status = p.status()

        if status == psutil.STATUS_STOPPED:
            return "Stopped"
        elif status in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
            return "Running"
        elif status in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD):
            return "Terminated"
        return status

    except psutil.NoSuchProcess:
        log.debug(f"Process {pid} not found. Marked as Terminated.")
        return "Terminated"
    except Exception as e:
        log.error(f"Error getting status for PID {pid}: {e}")
        return "Unknown"