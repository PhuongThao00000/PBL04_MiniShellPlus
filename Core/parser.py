import os
import shlex


def parse_command(line):
    """
    Parse command line into pipeline segments and background flag.
    Returns: (segments: list, background: bool)
    """
    line = line.strip()
    if not line:
        return [], False

    background = line.endswith("&")
    if background:
        line = line[:-1].strip()

    try:
        lex = shlex.shlex(line, posix=True)
        lex.whitespace_split = True
        lex.commenters = ""
        tokens = list(lex)
    except ValueError:
        # Quote không khớp - trả về empty (đã xử lý ở shell.py)
        return [], False

    segments, cur = [], []
    for tok in tokens:
        if tok == "|":
            segments.append(" ".join(cur))
            cur = []
        else:
            cur.append(tok)
    if cur:
        segments.append(" ".join(cur))

    return segments, background


def build_popen_args(cmd_str):
    """
    Parse redirections from command string.
    Returns: (args: list, stdin_file, stdout_file)
    """
    try:
        tokens = shlex.split(cmd_str, posix=True)
    except ValueError:
        # Quote không khớp - trả về None
        return None, None, None

    args, stdin_f, stdout_f = [], None, None
    i = 0

    while i < len(tokens):
        tok = tokens[i]
        try:
            if tok == "<":
                if i + 1 >= len(tokens):
                    print("minishell: syntax error: expected filename after '<'")
                    return None, None, None
                stdin_f = open(os.path.expanduser(tokens[i + 1]), "rb")
                i += 2
            elif tok == ">":
                if i + 1 >= len(tokens):
                    print("minishell: syntax error: expected filename after '>'")
                    return None, None, None
                stdout_f = open(os.path.expanduser(tokens[i + 1]), "wb")
                i += 2
            elif tok == ">>":
                if i + 1 >= len(tokens):
                    print("minishell: syntax error: expected filename after '>>'")
                    return None, None, None
                stdout_f = open(os.path.expanduser(tokens[i + 1]), "ab")
                i += 2
            else:
                args.append(tok)
                i += 1
        except (IndexError, OSError) as e:
            print(f"minishell: redirection error: {e}")
            # Đóng các file đã mở
            if stdin_f:
                stdin_f.close()
            if stdout_f:
                stdout_f.close()
            return None, None, None

    return args, stdin_f, stdout_f