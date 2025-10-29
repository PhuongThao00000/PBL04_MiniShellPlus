# core/__init__.py
import signal
print("Core package loaded.")
signal.signal(signal.SIGINT, lambda s, f: print("\nInterrupted!"))
