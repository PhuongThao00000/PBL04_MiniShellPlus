#!/usr/bin/env python3
import psutil
import time
import os
from datetime import datetime

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def bytes_to_mb(bytes_value):
    return round(bytes_value / (1024 * 1024), 2)

def show_processes():
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'create_time']):
        try:
            pinfo = proc.info
            pinfo['create_time'] = datetime.fromtimestamp(pinfo['create_time']).strftime("%H:%M:%S")
            processes.append(pinfo)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    processes = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)

    print(f"{'PID':<8} {'Name':<25} {'CPU%':<8} {'RAM%':<8} {'Status':<12} {'Started':<10}")
    print("=" * 75)

    for p in processes[:20]:  # Hiển thị top 20 tiến trình
        print(f"{p['pid']:<8} {p['name'][:24]:<25} {p['cpu_percent']:<8} {round(p['memory_percent'], 1):<8} {p['status']:<12} {p['create_time']:<10}")

if __name__ == "__main__":
    try:
        while True:
            clear_screen()
            print("=== PROCESS MONITOR ===")
            show_processes()
            time.sleep(3)  # cập nhật mỗi 3 giây
    except KeyboardInterrupt:
        print("\nProcess Monitor stopped.")
