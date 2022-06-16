import subprocess

subprocess.run(["black", "."])
subprocess.run(["isort", "."])
subprocess.run(["flake8"])
