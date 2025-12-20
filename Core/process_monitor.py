
import curses
import psutil
import time
import os
from datetime import datetime, timedelta


class ProcessMonitor:
    """Process Monitor with curses-based UI"""
    
    def __init__(self, refresh_interval=1.5):
        self.refresh_interval = refresh_interval
        self.filter_mode = None  # None, 'name', 'cpu', 'mem'
        self.filter_text = ""
        self.sort_by = 'cpu'  # Default sort by CPU
        self.processes = []
        self.scroll_offset = 0
        
    def get_processes_info(self):
        """Gather process information using psutil"""
        processes = []
        
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
                
                process_data = {
                    'pid': pinfo.get('pid', 0),
                    'user': pinfo.get('username', 'N/A')[:8],
                    'cpu': pinfo.get('cpu_percent', 0.0),
                    'mem': pinfo.get('memory_percent', 0.0),
                    'status': pinfo.get('status', 'N/A')[:4],
                    'runtime': runtime_str,
                    'threads': pinfo.get('num_threads', 0),
                    'io_read': io_read,
                    'io_write': io_write,
                    'command': command,
                    'name': pinfo.get('name', 'N/A')
                }
                
                processes.append(process_data)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Silently skip processes we can't access
                # This is expected behavior for system processes
                continue
        
        return processes
    
    def _format_runtime(self, seconds):
        """Format runtime in human-readable format"""
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
        """Format bytes in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f}PB"
    
    def _get_max_scroll(self):
        """Calculate maximum scroll offset for current process list"""
        return max(0, len(self.processes) - 1)
    
    def filter_processes(self, processes):
        """Apply filters to process list"""
        if self.filter_mode == 'name' and self.filter_text:
            # Filter by name
            processes = [p for p in processes 
                        if self.filter_text.lower() in p['name'].lower() or 
                           self.filter_text.lower() in p['command'].lower()]
        elif self.filter_mode == 'cpu':
            # Sort by CPU (top consumers)
            processes = sorted(processes, key=lambda x: x['cpu'], reverse=True)[:50]
        elif self.filter_mode == 'mem':
            # Sort by Memory (top consumers)
            processes = sorted(processes, key=lambda x: x['mem'], reverse=True)[:50]
        else:
            # Default sort by CPU
            processes = sorted(processes, key=lambda x: x['cpu'], reverse=True)
        
        return processes
    
    def draw_gauge(self, stdscr, y, x, label, value, max_width=30):
        """Draw a horizontal gauge bar"""
        try:
            # Draw label
            stdscr.addstr(y, x, f"{label}: ", curses.color_pair(1) | curses.A_BOLD)
            
            # Calculate bar width
            filled = int((value / 100.0) * max_width)
            
            # Choose color based on value
            if value < 50:
                color = curses.color_pair(2)  # Green
            elif value < 80:
                color = curses.color_pair(3)  # Yellow
            else:
                color = curses.color_pair(4)  # Red
            
            # Draw bar
            bar = "█" * filled + "░" * (max_width - filled)
            stdscr.addstr(y, x + len(label) + 2, bar, color)
            
            # Draw percentage
            stdscr.addstr(y, x + len(label) + 2 + max_width + 1, f"{value:5.1f}%")
        except curses.error:
            pass
    
    def draw_header(self, stdscr, height, width):
        """Draw the header with system information and gauges"""
        try:
            # Title
            title = "═══ MiniShell Process Monitor ═══"
            stdscr.addstr(0, (width - len(title)) // 2, title, 
                         curses.color_pair(1) | curses.A_BOLD)
            
            # System CPU and Memory (non-blocking call)
            cpu_percent = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            mem_percent = mem.percent
            
            # Draw gauges
            self.draw_gauge(stdscr, 1, 2, "CPU", cpu_percent, 30)
            self.draw_gauge(stdscr, 2, 2, "MEM", mem_percent, 30)
            
            # System info
            stdscr.addstr(1, width - 30, f"Refresh: {self.refresh_interval}s")
            stdscr.addstr(2, width - 30, f"Processes: {len(self.processes)}")
            
            # Filter info
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
            
            # Controls
            controls = "Controls: [/]Search [c]CPU [m]Memory [r]Reset [+/-]Interval [q]Quit"
            stdscr.addstr(4, 2, controls, curses.color_pair(5))
            
            # Column headers
            header = f"{'PID':<8} {'USER':<10} {'%CPU':<7} {'%MEM':<7} {'STAT':<6} {'RUNTIME':<12} {'THR':<5} {'I/O READ':<10} {'I/O WRITE':<10} {'COMMAND':<30}"
            stdscr.addstr(5, 0, header, curses.color_pair(1) | curses.A_BOLD | curses.A_REVERSE)
            
        except curses.error:
            pass
    
    def draw_processes(self, stdscr, height, width, start_row=6):
        """Draw the process list"""
        max_rows = height - start_row - 1
        
        for idx, proc in enumerate(self.processes[self.scroll_offset:self.scroll_offset + max_rows]):
            row = start_row + idx
            if row >= height - 1:
                break
            
            try:
                # Format process line
                line = f"{proc['pid']:<8} {proc['user']:<10} {proc['cpu']:<7.1f} {proc['mem']:<7.1f} {proc['status']:<6} {proc['runtime']:<12} {proc['threads']:<5} {proc['io_read']:<10} {proc['io_write']:<10} {proc['command']:<30}"
                
                # Truncate if too long
                if len(line) > width:
                    line = line[:width-1]
                
                # Color based on CPU usage
                if proc['cpu'] > 80:
                    color = curses.color_pair(4)  # Red
                elif proc['cpu'] > 50:
                    color = curses.color_pair(3)  # Yellow
                else:
                    color = curses.color_pair(0)  # Normal
                
                stdscr.addstr(row, 0, line, color)
                
            except curses.error:
                pass
    
    def handle_input(self, stdscr, key):
        """Handle keyboard input"""
        if key == ord('q'):
            return False  # Exit
        elif key == ord('r'):
            # Reset filter
            self.filter_mode = None
            self.filter_text = ""
            self.scroll_offset = 0
        elif key == ord('c'):
            # Filter by CPU
            self.filter_mode = 'cpu'
            self.filter_text = ""
            self.scroll_offset = 0
        elif key == ord('m'):
            # Filter by Memory
            self.filter_mode = 'mem'
            self.filter_text = ""
            self.scroll_offset = 0
        elif key == ord('/'):
            # Search by name
            self.filter_mode = 'name'
            curses.echo()
            stdscr.addstr(0, 0, "Search: ", curses.color_pair(1))
            stdscr.clrtoeol()
            try:
                self.filter_text = stdscr.getstr(0, 8, 30).decode('utf-8')
            except (UnicodeDecodeError, KeyboardInterrupt):
                self.filter_text = ""
            curses.noecho()
            self.scroll_offset = 0
        elif key == ord('+') or key == ord('='):
            # Increase refresh interval
            self.refresh_interval = min(10.0, self.refresh_interval + 0.5)
        elif key == ord('-') or key == ord('_'):
            # Decrease refresh interval
            self.refresh_interval = max(0.5, self.refresh_interval - 0.5)
        elif key == curses.KEY_UP:
            # Scroll up
            self.scroll_offset = max(0, self.scroll_offset - 1)
        elif key == curses.KEY_DOWN:
            # Scroll down
            self.scroll_offset = min(self._get_max_scroll(), self.scroll_offset + 1)
        elif key == curses.KEY_PPAGE:  # Page Up
            self.scroll_offset = max(0, self.scroll_offset - 10)
        elif key == curses.KEY_NPAGE:  # Page Down
            self.scroll_offset = min(self._get_max_scroll(), self.scroll_offset + 10)
        
        return True  # Continue
    
    def run(self, stdscr):
        """Main loop for the process monitor"""
        # Initialize colors
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        
        # Setup
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)  # Non-blocking input
        stdscr.timeout(int(self.refresh_interval * 1000))
        
        # Initialize CPU monitoring for non-blocking calls
        psutil.cpu_percent(interval=None)
        
        running = True
        while running:
            try:
                # Get terminal size
                height, width = stdscr.getmaxyx()
                
                # Clear screen
                stdscr.clear()
                
                # Get and filter processes
                all_processes = self.get_processes_info()
                self.processes = self.filter_processes(all_processes)
                
                # Draw UI
                self.draw_header(stdscr, height, width)
                self.draw_processes(stdscr, height, width)
                
                # Draw status bar
                try:
                    status = f"Displaying {len(self.processes)} processes | Scroll: {self.scroll_offset}"
                    stdscr.addstr(height - 1, 0, status, curses.color_pair(5))
                except curses.error:
                    pass
                
                # Refresh screen
                stdscr.refresh()
                
                # Handle input
                key = stdscr.getch()
                if key != -1:
                    running = self.handle_input(stdscr, key)
                    # Update timeout based on new interval
                    stdscr.timeout(int(self.refresh_interval * 1000))
                
            except KeyboardInterrupt:
                break
            except (curses.error, OSError) as e:
                # Display curses or system errors
                try:
                    stdscr.addstr(0, 0, f"Error: {str(e)}")
                    stdscr.refresh()
                    time.sleep(2)
                except curses.error:
                    # Screen too small to display error, continue anyway
                    pass


def start_process_monitor(refresh_interval=1.5):
    """Start the process monitor with curses"""
    try:
        monitor = ProcessMonitor(refresh_interval)
        curses.wrapper(monitor.run)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error starting process monitor: {e}")
