import subprocess
import os
import signal
import sys
import psutil
from enum import Enum
from typing import Dict, List, Optional

from . import log
from .utils import get_process_status



class JobStatus(Enum):
    RUNNING = "Running"
    STOPPED = "Stopped"
    DONE = "Done"
    TERMINATED = "Terminated"


class Job:

    def __init__(self, jid: int, process: subprocess.Popen, command: str):
        self.jid = jid
        self.process = process
        self.pid = process.pid
        self.pgid = os.getpgid(self.pid)
        self.command = command
        self.status = JobStatus.RUNNING

    def __str__(self):
        return f"[{self.jid}]\t{self.pid}\t{self.status.value}\t{self.command}"

    def update_status(self):
        if self.status in [JobStatus.DONE, JobStatus.TERMINATED]:
            return

        return_code = self.process.poll()

        if return_code is None:
            real_status = get_process_status(self.pid)
            if real_status == "Stopped":
                self.status = JobStatus.STOPPED
            else:
                self.status = JobStatus.RUNNING
        else:
            if return_code == 0:
                self.status = JobStatus.DONE
            else:
                self.status = JobStatus.TERMINATED


class JobManager:

    def __init__(self):
        self.jobs: Dict[int, Job] = {}
        self.next_jid = 1
        self.shell_pgid = os.getpgrp()
        log.info(f"Job Manager initialized (PID: {self.shell_pgid}, Platform: Linux/Unix).")

    def register_job(self, process: subprocess.Popen, command: str) -> Optional[Job]:
        if not process:
            return None

        jid = self.next_jid
        self.next_jid += 1

        job = Job(jid, process, command)
        self.jobs[jid] = job

        log.info(f"Registered new job: {job}")
        return job

    def _cleanup_finished_jobs(self):
        finished_jids = [
            jid for jid, job in self.jobs.items()
            if job.status in (JobStatus.DONE, JobStatus.TERMINATED)
        ]

        for jid in finished_jids:
            log.info(f"Cleaning up finished job [{jid}].")
            del self.jobs[jid]

    def update_all_statuses(self):
        if not self.jobs:
            return

        log.debug("Updating all job statuses...")
        for job in self.jobs.values():
            job.update_status()

        self._cleanup_finished_jobs()

    def list_jobs(self) -> List[str]:
        self.update_all_statuses()
        if not self.jobs:
            return ["No active jobs."]

        return [str(job) for job in self.jobs.values()]

    def get_job_by_id(self, jid_str: str) -> Optional[Job]:
        try:
            jid = int(jid_str)
            job = self.jobs.get(jid)
            if not job:
                log.warning(f"No job found with JID: {jid}")
            return job
        except ValueError:
            log.error(f"Invalid JID: {jid_str}")
            return None

    def send_signal_to_job(self, jid_str: str, signal_type: int) -> str:
        job = self.get_job_by_id(jid_str)
        if not job:
            return f"Job not found: {jid_str}"

        if job.status in (JobStatus.DONE, JobStatus.TERMINATED):
            return f"Job {jid_str} is already finished."

        try:
            os.killpg(job.pgid, signal_type)

            log.info(f"Sent signal {signal_type} to job [{job.jid}] (PID {job.pid})")
            job.update_status()
            return f"Sent signal {signal_type} to job {job.jid}."

        except ProcessLookupError:
            log.error(f"Process {job.pid} not found while sending signal.")
            job.status = JobStatus.TERMINATED
            return f"Process for job {job.jid} not found."
        except Exception as e:
            log.error(f"Error sending signal to {job.jid}: {e}")
            return f"Error sending signal: {e}"

    def bring_to_foreground(self, jid_str: str) -> str:
        job = self.get_job_by_id(jid_str)
        if not job:
            return f"fg: job not found: {jid_str}"

        if job.status == JobStatus.STOPPED:
            self.send_signal_to_job(jid_str, signal.SIGCONT)

        try:
            # Giao quyền kiểm soát terminal
            os.tcsetpgrp(sys.stdin.fileno(), job.pgid)
        except Exception as e:
            log.error(f"Failed to set terminal control: {e}")
            return f"Error: {e}"

        try:
            # Chờ đợi, WUNTRACED là để bắt cả tín hiệu STOP (Ctrl+Z)
            _, status = os.waitpid(job.pid, os.WUNTRACED)
        except ChildProcessError:
            pass  # Tiến trình đã kết thúc

        # Lấy lại quyền kiểm soát terminal cho Shell
        os.tcsetpgrp(sys.stdin.fileno(), self.shell_pgid)

        job.update_status()

        if job.status == JobStatus.STOPPED:
            print(f"\nStopped: {job.command}")

        return ""


# TẠO MỘT INSTANCE (THỂ HIỆN) DUY NHẤT CỦA JOB MANAGER
job_manager = JobManager()