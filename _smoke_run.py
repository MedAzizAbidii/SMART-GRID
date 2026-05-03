import os, sys, time, signal, subprocess
cmd = [sys.executable, "-u", "smart_meters_simulator.py"]
flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP") else 0
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, creationflags=flags)
lines = []
start = time.time()
while time.time() - start < 7:
    line = p.stdout.readline()
    if line:
        lines.append(line.rstrip("\n"))
    elif p.poll() is not None:
        break
if p.poll() is None:
    try:
        p.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)
        p.wait(timeout=5)
    except Exception:
        p.terminate(); p.wait(timeout=5)
extra = []
try:
    tail, _ = p.communicate(timeout=1)
    if tail:
        extra = [x for x in tail.splitlines() if x]
except Exception:
    pass
all_lines = lines + extra
print("LINES_CAPTURED=" + str(len(all_lines)))
print("EXIT_CODE=" + str(p.returncode))
print("---HEAD---")
for ln in all_lines[:25]:
    print(ln)
print("---TAIL---")
for ln in all_lines[-20:]:
    print(ln)
