import os

def get_prompt():
    user = os.getenv("USER", "user")
    cwd = os.getcwd()
    base = os.path.basename(cwd)
    return f"{user}@minishell:{base}$ "
