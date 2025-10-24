import os, shlex

def build_popen_args(cmd_str):
    tokens = shlex.split(cmd_str)
    args, stdin_f, stdout_f = [], None, None
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "<":
            stdin_f = open(os.path.expanduser(tokens[i+1]), "rb")
            i += 2
        elif tok == ">":
            stdout_f = open(os.path.expanduser(tokens[i+1]), "wb")
            i += 2
        elif tok == ">>":
            stdout_f = open(os.path.expanduser(tokens[i+1]), "ab")
            i += 2
        else:
            args.append(tok)
            i += 1
    return args, stdin_f, stdout_f
