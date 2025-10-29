import os
import sys

try:
    import readline
except ImportError:
    print("Lỗi: Vui lòng cài đặt 'readline' (thường đi kèm Python trên Linux).")
    sys.exit(1)

HIST_FILE = os.path.join(os.path.expanduser("~"), ".minishell_plus_history")


def init_history():
    try:
        # Đặt giới hạn lịch sử
        readline.set_history_length(1000)
    except Exception as e:
        print(f"Lỗi khi khởi tạo history: {e}")


def load_history():
    try:
        readline.read_history_file(HIST_FILE)
    except FileNotFoundError:
        pass  # Không sao nếu tệp chưa tồn tại
    except Exception as e:
        print(f"Lỗi khi tải tệp lịch sử: {e}")


def add_history(line: str):
    if line.strip():  # Chỉ thêm nếu dòng không rỗng
        readline.add_history(line)


def save_history_file():
    try:
        readline.write_history_file(HIST_FILE)
    except Exception as e:
        print(f"Lỗi khi lưu tệp lịch sử: {e}")


def show_history():
    print("--- Lịch sử lệnh ---")
    length = readline.get_current_history_length()
    if length == 0:
        print("(Trống)")
        return

    for i in range(1, length + 1):
        # Lấy item bắt đầu từ 1
        print(f" {i}\t{readline.get_history_item(i)}")