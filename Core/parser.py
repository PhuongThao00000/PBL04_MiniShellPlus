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

    lex = shlex.shlex(line, posix=True)
    lex.whitespace_split = True
    lex.commenters = ""
    tokens = list(lex)

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
    tokens = shlex.split(cmd_str, posix=True)
    args, stdin_f, stdout_f = [], None, None
    i = 0

    while i < len(tokens):
        tok = tokens[i]
        try:
            if tok == "<":
                stdin_f = open(os.path.expanduser(tokens[i + 1]), "rb")
                i += 2
            elif tok == ">":
                stdout_f = open(os.path.expanduser(tokens[i + 1]), "wb")
                i += 2
            elif tok == ">>":
                stdout_f = open(os.path.expanduser(tokens[i + 1]), "ab")
                i += 2
            else:
                args.append(tok)
                i += 1
        except (IndexError, OSError) as e:
            print(f"minishell: redirection error: {e}")
            return None, None, None

    return args, stdin_f, stdout_f