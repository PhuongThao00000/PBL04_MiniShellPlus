
import curses
import psutil
import time
import sys


def show_process_monitor(stdscr):
    """
    Hàm này được gọi bởi curses, 'stdscr' là đối tượng màn hình.
    """
    # Cấu hình curses
    stdscr.nodelay(True)  # Không chặn khi chờ phím
    stdscr.clear()

    # Tắt hiển thị con trỏ
    curses.curs_set(0)

    try:
        while True:
            # 1. Kiểm tra phím bấm
            key = stdscr.getch()
            if key == ord('q'):  # Bấm 'q' để thoát
                break

            # 2. Xóa màn hình cũ
            stdscr.clear()

            # 3. Lấy thông tin hệ thống
            cpu_percent = psutil.cpu_percent(percpu=False)
            mem = psutil.virtual_memory()
            mem_percent = mem.percent

            # 4. Vẽ header (phần đầu)
            stdscr.addstr(0, 0, f"MiniShell Process Monitor (bấm 'q' để thoát)")
            stdscr.addstr(1, 0, f"CPU: [{cpu_percent:5.1f}%] {'#' * int(cpu_percent / 4)}")
            stdscr.addstr(2, 0, f"MEM: [{mem_percent:5.1f}%] {'#' * int(mem_percent / 4)}")
            stdscr.addstr(4, 0, "PID\tUSER\t\t%CPU\t%MEM\tCOMMAND")
            stdscr.addstr(5, 0, "-" * 60)

            # 5. Lấy và sắp xếp danh sách tiến trình
            procs = []
            for p in psutil.process_iter(['pid', 'username', 'cpu_percent', 'memory_percent', 'name']):
                procs.append(p.info)

            # Sắp xếp theo %CPU giảm dần
            procs_sorted = sorted(procs, key=lambda x: x['cpu_percent'], reverse=True)

            # 6. Vẽ danh sách tiến trình (chỉ 10 tiến trình đầu)
            row = 6
            for p in procs_sorted[:10]:
                user = p['username'] if p['username'] else 'N/A'
                # Giới hạn độ dài tên
                user_str = user[:10]
                cmd_str = p['name'][:20]

                line = f"{p['pid']:<5}\t{user_str:<10}\t{p['cpu_percent']:>5.1f}\t{p['memory_percent']:>5.1f}\t{cmd_str}"
                stdscr.addstr(row, 0, line)
                row += 1

            # 7. Cập nhật màn hình
            stdscr.refresh()

            # 8. Ngủ 1 giây
            time.sleep(1)

    except KeyboardInterrupt:
        pass  # Thoát khi bấm Ctrl+C
    except Exception as e:
        # Phải thoát curses trước khi in lỗi
        curses.endwin()
        print(f"Lỗi TUI: {e}")
        sys.exit(1)


def start_tui():
    """Hàm bao bọc để khởi động và dọn dẹp curses an toàn."""
    # curses.wrapper sẽ tự động khởi tạo,
    # chạy hàm 'show_process_monitor',
    # và tự động dọn dẹp (curses.endwin) khi kết thúc
    try:
        curses.wrapper(show_process_monitor)
    except curses.error:
        print("Lỗi: Không thể khởi động Curses.")
