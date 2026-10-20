import subprocess
import time
import sys

p = subprocess.Popen([r"c:\Users\ozan.gemici\Downloads\Telegram Desktop\v4.82Dogruer_MasterSuite_Workspace\v4.0Dogruer_MasterSuite_Workspace\Dogruer_MasterSuite_Workspace\python-embed\python.exe", "tools/dogruer_online_bridge/dogruer_pyqt_embed.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

time.sleep(3)
print('Sending AUTO_LOGIN')
p.stdin.write('AUTO_LOGIN\n')
p.stdin.flush()
time.sleep(5)

# Try reading output
import fcntl, os
# Wait, fcntl is not on Windows. We will use threads to read.

