
from .logger import get_monitor_logger

# Khởi tạo một logger chung để các module con có thể import và sử dụng
log = get_monitor_logger()

log.info("Process Monitor package loaded.")