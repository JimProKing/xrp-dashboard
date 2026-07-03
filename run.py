import subprocess
import sys
import time

import uvicorn

HOST = "127.0.0.1"
PORT = 8000


def free_port(port: int) -> None:
    if sys.platform != "win32":
        return
    ps_cmd = (
        f"$pids = Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue "
        "| Select-Object -ExpandProperty OwningProcess -Unique; "
        "foreach ($procId in $pids) { "
        "if ($procId -gt 0) { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue } }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    time.sleep(1)


if __name__ == "__main__":
    free_port(PORT)
    print(f"\n  XRP Dashboard: http://{HOST}:{PORT}\n")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)