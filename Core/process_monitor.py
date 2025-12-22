
import curses
import psutil
import time
import os
from datetime import datetime, timedelta


class ProcessMonitor:

    def __init__(self, refresh_interval=1.5):
        self.refresh_interval = refresh_interval
        self.filter_mode = None  # None, 'name', 'cpu', 'mem'
        self.filter_text = ""
        self.sort_by = 'cpu'  # Default sort by CPU
        self.processes = []
        self.scroll_offset = 0

    def get_processes_info(self):
        processes = []

        # Lấy thông tin processes
        for proc in psutil.process_iter(['pid', 'username', 'name', 'cpu_percent',
                                         'memory_percent', 'status', 'create_time',
                                         'num_threads', 'io_counters', 'cmdline']):
            try:
                pinfo = proc.info

                # Calculate runtime
                create_time = pinfo.get('create_time', 0)
                if create_time:
                    runtime = time.time() - create_time
                    runtime_str = self._format_runtime(runtime)
                else:
                    runtime_str = "N/A"

                # Get I/O counters
                io_counters = pinfo.get('io_counters')
                if io_counters:
                    io_read = self._format_bytes(io_counters.read_bytes)
                    io_write = self._format_bytes(io_counters.write_bytes)
                else:
                    io_read = "N/A"
                    io_write = "N/A"

                # Get command line
                cmdline = pinfo.get('cmdline')
                if cmdline:
                    command = ' '.join(cmdline)
                else:
                    command = pinfo.get('name', 'N/A')

                # Truncate long commands
                if len(command) > 60:
                    command = command[:57] + "..."

                status_str = pinfo.get('status', 'N/A')

                process_data = {
                    'pid': pinfo.get('pid', 0),
                    'user': pinfo.get('username', 'N/A')[:8],
                    'cpu': pinfo.get('cpu_percent', 0.0),
                    'mem': pinfo.get('memory_percent', 0.0),
                    'status': status_str,  # Sử dụng chuỗi đầy đủ
                    'runtime': runtime_str,
                    'threads': pinfo.get('num_threads', 0),
                    'io_read': io_read,
                    'io_write': io_write,
                    'command': command,
                    'name': pinfo.get('name', 'N/A')
                }

                processes.append(process_data)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return processes

    def _format_runtime(self, seconds):
        td = timedelta(seconds=int(seconds))
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if days > 0:
            return f"{days}d {hours:02d}:{minutes:02d}"
        elif hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def _format_bytes(self, bytes_value):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f}PB"

    def _get_max_scroll(self):
        return max(0, len(self.processes) - 1)

    def filter_processes(self, processes):
        if self.filter_mode == 'name' and self.filter_text:
            processes = [p for p in processes
                         if self.filter_text.lower() in p['name'].lower() or
                         self.filter_text.lower() in p['command'].lower()]
        elif self.filter_mode == 'cpu':
            processes = sorted(processes, key=lambda x: x['cpu'], reverse=True)[:50]
        elif self.filter_mode == 'mem':
            processes = sorted(processes, key=lambda x: x['mem'], reverse=True)[:50]
        else:
            processes = sorted(processes, key=lambda x: x['cpu'], reverse=True)
        return processes

    def draw_gauge(self, stdscr, y, x, label, value, max_width=30):
        try:
            stdscr.addstr(y, x, f"{label}: ", curses.color_pair(1) | curses.A_BOLD)
            filled = int((value / 100.0) * max_width)
            filled = max(0, min(filled, max_width))

            if value < 50:
                color = curses.color_pair(2)
            elif value < 80:
                color = curses.color_pair(3)
            else:
                color = curses.color_pair(4)

            bar = "█" * filled + "░" * (max_width - filled)
            stdscr.addstr(y, x + len(label) + 2, bar, color)
            stdscr.addstr(y, x + len(label) + 2 + max_width + 1, f"{value:5.1f}%")
        except curses.error:
            pass

    def draw_header(self, stdscr, height, width):
        try:
            title = "═══ MiniShell Process Monitor ═══"
            stdscr.addstr(0, (width - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)

            cpu_percent = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            mem_percent = mem.percent

            self.draw_gauge(stdscr, 1, 2, "CPU", cpu_percent, 30)
            self.draw_gauge(stdscr, 2, 2, "MEM", mem_percent, 30)

            stdscr.addstr(1, width - 30, f"Refresh: {self.refresh_interval}s")
            stdscr.addstr(2, width - 30, f"Processes: {len(self.processes)}")

            filter_info = "Filter: "
            if self.filter_mode == 'name':
                filter_info += f"Name '{self.filter_text}'"
            elif self.filter_mode == 'cpu':
                filter_info += "Top CPU"
            elif self.filter_mode == 'mem':
                filter_info += "Top Memory"
            else:
                filter_info += "None"
            stdscr.addstr(3, 2, filter_info, curses.color_pair(3))

            controls = "Controls: [/]Search [c]CPU [m]Memory [r]Reset [+/-]Interval [q]Quit"
            stdscr.addstr(4, 2, controls, curses.color_pair(5))

            header = f"{'PID':<8} {'USER':<10} {'%CPU':<7} {'%MEM':<7} {'STATUS':<12} {'RUNTIME':<12} {'THR':<5} {'I/O READ':<10} {'I/O WRITE':<10} {'COMMAND':<30}"
            stdscr.addstr(5, 0, header, curses.color_pair(1) | curses.A_BOLD | curses.A_REVERSE)

        except curses.error:
            pass

    def draw_processes(self, stdscr, height, width, start_row=6):
        max_rows = height - start_row - 1

        for idx, proc in enumerate(self.processes[self.scroll_offset:self.scroll_offset + max_rows]):
            row = start_row + idx
            if row >= height - 1:
                break

            try:
                line = f"{proc['pid']:<8} {proc['user']:<10} {proc['cpu']:<7.1f} {proc['mem']:<7.1f} {proc['status']:<12} {proc['runtime']:<12} {proc['threads']:<5} {proc['io_read']:<10} {proc['io_write']:<10} {proc['command']:<30}"

                if len(line) > width:
                    line = line[:width - 1]

                if proc['cpu'] > 80:
                    color = curses.color_pair(4)
                elif proc['cpu'] > 50:
                    color = curses.color_pair(3)
                else:
                    color = curses.color_pair(0)

                stdscr.addstr(row, 0, line, color)

            except curses.error:
                pass

    def draw_status_bar(self, stdscr, height, width):
        try:
            left_info = f" COUNT: {len(self.processes)} "

            if self.filter_mode == 'name':
                mid_info = f" FILTER: Name contains '{self.filter_text}' "
            elif self.filter_mode == 'cpu':
                mid_info = " FILTER: Top 50 CPU "
            elif self.filter_mode == 'mem':
                mid_info = " FILTER: Top 50 MEM "
            else:
                mid_info = " MODE: All Processes "

            right_info = f" SCROLL: {self.scroll_offset}/{self._get_max_scroll()} | [q] Quit "

            content_len = len(left_info) + len(mid_info) + len(right_info)
            remaining_space = width - content_len

            if remaining_space > 0:
                pad_left = " " * (remaining_space // 2)
                pad_right = " " * (remaining_space - len(pad_left))
                status_str = f"{left_info}{pad_left}{mid_info}{pad_right}{right_info}"
            else:
                status_str = (left_info + mid_info + right_info)[:width - 1]

            stdscr.addstr(height - 1, 0, status_str, curses.color_pair(5) | curses.A_REVERSE | curses.A_BOLD)
        except curses.error:
            pass

    def live_search(self, stdscr):
        curses.curs_set(1)
        self.filter_mode = 'name'
        self.filter_text = ""
        current_snapshot = self.get_processes_info()

        while True:
            self.processes = self.filter_processes(current_snapshot)
            self.scroll_offset = 0

            height, width = stdscr.getmaxyx()
            stdscr.clear()
            self.draw_header(stdscr, height, width)
            self.draw_processes(stdscr, height, width)

            prompt = " SEARCH: "
            try:
                stdscr.addstr(height - 1, 0, " " * (width - 1), curses.color_pair(2) | curses.A_REVERSE)
                stdscr.addstr(height - 1, 0, prompt, curses.color_pair(2) | curses.A_REVERSE | curses.A_BOLD)
                stdscr.addstr(height - 1, len(prompt), self.filter_text, curses.color_pair(0) | curses.A_REVERSE)
            except curses.error:
                pass

            stdscr.refresh()
            key = stdscr.getch()

            if key in [10, 13]:
                break
            elif key == 27:
                self.filter_mode = None
                self.filter_text = ""
                break
            elif key in [curses.KEY_BACKSPACE, 127, 8]:
                self.filter_text = self.filter_text[:-1]
            elif 32 <= key <= 126:
                self.filter_text += chr(key)

        curses.curs_set(0)

    def handle_input(self, stdscr, key):
        if key == ord('q'):
            return False
        elif key == ord('r'):
            self.filter_mode = None;
            self.filter_text = "";
            self.scroll_offset = 0
        elif key == ord('c'):
            self.filter_mode = 'cpu';
            self.filter_text = "";
            self.scroll_offset = 0
        elif key == ord('m'):
            self.filter_mode = 'mem';
            self.filter_text = "";
            self.scroll_offset = 0
        elif key == ord('/'):
            self.live_search(stdscr)
        elif key == ord('+') or key == ord('='):
            self.refresh_interval = min(10.0, self.refresh_interval + 0.5)
        elif key == ord('-') or key == ord('_'):
            self.refresh_interval = max(0.5, self.refresh_interval - 0.5)
        elif key == curses.KEY_UP:
            self.scroll_offset = max(0, self.scroll_offset - 1)
        elif key == curses.KEY_DOWN:
            self.scroll_offset = min(self._get_max_scroll(), self.scroll_offset + 1)
        elif key == curses.KEY_PPAGE:
            self.scroll_offset = max(0, self.scroll_offset - 10)
        elif key == curses.KEY_NPAGE:
            self.scroll_offset = min(self._get_max_scroll(), self.scroll_offset + 10)
        return True

    def run(self, stdscr):
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)

        curses.curs_set(0);
        stdscr.nodelay(1);
        stdscr.timeout(int(self.refresh_interval * 1000))
        psutil.cpu_percent(interval=None)

        running = True
        while running:
            try:
                height, width = stdscr.getmaxyx()
                stdscr.clear()
                all_processes = self.get_processes_info()
                self.processes = self.filter_processes(all_processes)
                self.draw_header(stdscr, height, width)
                self.draw_processes(stdscr, height, width)
                self.draw_status_bar(stdscr, height, width)
                stdscr.refresh()
                key = stdscr.getch()
                if key != -1:
                    running = self.handle_input(stdscr, key)
                    stdscr.timeout(int(self.refresh_interval * 1000))
            except KeyboardInterrupt:
                break
            except (curses.error, OSError) as e:
                try:
                    stdscr.addstr(0, 0, f"Error: {str(e)}")
                    stdscr.refresh();
                    time.sleep(2)
                except curses.error:
                    pass


def start_process_monitor(refresh_interval=1.5):
    try:
        monitor = ProcessMonitor(refresh_interval)
        curses.wrapper(monitor.run)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error starting process monitor: {e}")


if __name__ == "__main__":
    start_process_monitor()