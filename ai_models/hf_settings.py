import os

HF_TOKEN = os.getenv("HF_API_KEY")
HF_USERNAME = os.getenv("HF_USERNAME", "vansh-here")

def repo(name):
    return f"{HF_USERNAME}/{name}"
