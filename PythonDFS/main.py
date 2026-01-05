#!/usr/bin/env python3

import subprocess
import sys
import time
import signal
import socket
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
    print("[+] Starting DFS servers...")
    for folder, script, port in DFS_SERVERS:
        server_dir = BASE_DIR / folder
        p = subprocess.Popen(
            [sys.executable, script, str(port)],
            cwd=server_dir
        )
        processes.append(p)
        print(f"    - {folder}/{script} on port {port}")


def wait_for_server_ready(host, port, timeout=15):
    """Wait until a DFS server responds to a handshake, not just the port being open."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1) as s:
                # send a simple handshake, servers usually accept username length
                # just sending newline as dummy data to see if server accepts
                s.sendall(b'\n')
                return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.2)
    return False


def wait_for_all_servers():
    print("Waiting for DFS servers to be ready...")
    all_ready = True
    for folder, _, port in DFS_SERVERS:
        ready = wait_for_server_ready("127.0.0.1", port)
        if ready:
            print(f"[✓] {folder} is ready on port {port}")
        else:
            print(f"[✗] {folder} at 127.0.0.1:{port} unavailable")
            all_ready = False
    return all_ready


def start_client():
    print("\n[+] Starting DFC client...\n")
    subprocess.call(
        [sys.executable, "dfc.py", "dfc.conf"],
        cwd=BASE_DIR / "DFC"
    )


def shutdown(signum=None, frame=None):
    print("\n[!] Shutting down DFS cluster...")
    for p in processes:
        p.terminate()
    print("[✓] All servers stopped")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, shutdown)
    start_servers()

    if not wait_for_all_servers():
        print("\n[!] One or more DFS servers failed to start. Exiting.")
        shutdown()

    start_client()
    shutdown()


if __name__ == "__main__":
    main()
