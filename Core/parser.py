import shlex

def parse_command(line):
    line = line.strip()
    if not line:
        return [], False
    background = line.endswith("&")
    if background:
        line = line[:-1].strip()
    tokens = list(shlex.shlex(line, posix=True))
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
