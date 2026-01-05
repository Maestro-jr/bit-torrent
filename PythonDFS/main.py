#!/usr/bin/env python3

import subprocess
import sys
import time
import signal
from pathlib import Path

BASE_DIR = Path(__file__).parent

DFS_SERVERS = [
    ("DFS1", "dfs1.py", 10001),
    ("DFS2", "dfs2.py", 10002),
    ("DFS3", "dfs3.py", 10003),
    ("DFS4", "dfs4.py", 10004),
]

processes = []


def start_servers():
    print("[+] Starting DFS servers...\n")

    for folder, script, port in DFS_SERVERS:
        server_dir = BASE_DIR / folder

        p = subprocess.Popen(
            [sys.executable, script, str(port)],
            cwd=server_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            if sys.platform == "win32" else 0
        )

        processes.append(p)
        print(f"    - {folder} started on port {port}")

    print("\n[✓] All DFS servers launched")
    print("Waiting for servers to initialize...\n")
    time.sleep(2)  # let servers bind and listen


def start_client():
    print("[+] Starting DFC client (interactive)...\n")

    subprocess.call(
        [sys.executable, "dfc.py", "dfc.conf"],
        cwd=BASE_DIR / "DFC"
    )


def shutdown():
    print("\n[!] Shutting down DFS cluster...")

    for p in processes:
        try:
            p.terminate()
        except Exception:
            pass

    print("[✓] All DFS servers stopped")
    sys.exit(0)


def main():
    try:
        start_servers()
        start_client()  # BLOCKS until user exits client
    except KeyboardInterrupt:
        pass
    finally:
        shutdown()


if __name__ == "__main__":
    main()
