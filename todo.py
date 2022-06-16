import subprocess
import sys

if "-p" in sys.argv:
    subprocess.run(["py", "-m", "reqman", "-path", ".", "-plt"])
else:
    subprocess.run(["py", "-m", "reqman", "-path", ".", "-ptd"])
