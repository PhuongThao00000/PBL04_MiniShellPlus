# config.py
# file cau hinh cho chuong trinh MiniShell Plus

import os

# ============================
#  CAC THONG SO CO BAN
# ============================

# dau nhac lenh (prompt)
PROMPT = "MiniShell> "

# thu muc mac dinh khi mo shell
DEFAULT_PATH = os.path.expanduser("~")

# file luu lich su lenh
HISTORY_FILE = os.path.expanduser("~/.minishell_history")

# gioi han so lenh duoc luu
HISTORY_LIMIT = 100

# co ghi log lenh khong (True / False)
LOG_ENABLE = True

# file ghi log (neu LOG_ENABLE = True)
LOG_FILE = os.path.expanduser("~/.minishell_log.txt")


# ============================
#  THONG SO LIEN QUAN TIEN TRINH
# ============================

# thoi gian cap nhat khi xem process monitor (giay)
PMON_INTERVAL = 1.5

# so luong tien trinh toi da hien thi
PMON_MAX = 20


# ============================
#  MAU CHU (cho dep)
# ============================

class Color:
    RESET = "\033[0m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"


# ============================
#  CAC ALIAS (lenh viet tat)
# ============================

ALIASES = {
    "ll": "ls -l",
    "cls": "clear",
    "gs": "git status"
}
