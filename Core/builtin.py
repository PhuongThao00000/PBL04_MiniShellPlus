import os
import shlex
from Core.history import show_history
from Core.job_control import show_jobs

# Alias dictionary
aliases = {}


def builtin_help():
    """Print help message"""
    print("""MiniShell help:
 Built-in commands:
  cd [dir]      : change directory
  exit          : exit shell
  help          : print this help
  history       : show command history
  pmon          : process monitor
  alias         : create or show aliases
  unalias       : remove aliases

Features:
  Pipes using |
  Redirection using > >> <
  Background with & (run command in background)
  sudo <cmd>    : run command with root privileges
""")


def builtin_cd(args):
    """Change directory"""
    path = args[0] if args else os.path.expanduser("~")
    try:
        os.chdir(os.path.expanduser(path))
        return 0
    except Exception as e:
        print(f"cd: {e}")
        return 1


def builtin_history():
    """Show command history"""
    show_history()
    return 0


def builtin_pmon():
    """Process monitor - show background jobs"""
    show_jobs()
    return 0


def builtin_alias(args):
    """Tạo hoặc xem alias"""
    if len(args) == 0:
        for k, v in aliases.items():
            print(f"alias {k}='{v}'")
    else:
        for arg in args:
            if '=' in arg:
                name, val = arg.split('=', 1)
                val = val.strip("'\"")
                aliases[name] = val
            else:
                if arg in aliases:
                    print(f"alias {arg}='{aliases[arg]}'")
                else:
                    print(f"alias: {arg}: not found")
    return 0


def builtin_unalias(args):
    """Xóa alias"""
    if not args:
        print("unalias: usage: unalias name")
        return 1
    for name in args:
        aliases.pop(name, None)
    return 0


def expand_alias(line):
    """
    Thay thế alias trong command line.
    Returns: expanded line
    """
    parts = shlex.split(line)
    if not parts:
        return line

    cmd = parts[0]
    if cmd in aliases:
        # Thay thế alias bằng giá trị thật
        expanded = aliases[cmd]
        if len(parts) > 1:
            # Giữ lại các arguments
            expanded += ' ' + ' '.join(parts[1:])
        return expanded
    return line


def execute_builtin(line):
    """
    Execute built-in command if it matches.
    Returns (executed: bool, exit_code: int)
    """
    parts = shlex.split(line)
    if not parts:
        return False, 0

    cmd = parts[0]
    args = parts[1:]

    builtins = {
        'help': lambda: builtin_help(),
        'history': lambda: builtin_history(),
        'pmon': lambda: builtin_pmon(),
        'exit': lambda: None,  # Handled in main loop
    }

    if cmd == 'cd':
        return True, builtin_cd(args)
    elif cmd == 'alias':
        return True, builtin_alias(args)
    elif cmd == 'unalias':
        return True, builtin_unalias(args)
    elif cmd in builtins:
        builtins[cmd]()
        return True, 0

    return False, 0