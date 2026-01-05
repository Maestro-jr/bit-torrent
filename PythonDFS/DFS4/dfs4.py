#! /usr/bin/env python3

"""
Distributed File System
Server 3
Fonyuy Berka
Jan 2026
(FIXED: Proper LIST logic + protocol alignment)
"""

# =========================
# MODULES
# =========================
import os
import pickle
import re
import sys
import time
import socket

# =========================
# STORAGE ROOT (DFS3)
# =========================
STORAGE_ROOT = r"C:\Users\HP\Desktop\Servers\Server 3"
os.makedirs(STORAGE_ROOT, exist_ok=True)

# =========================
# ARGUMENT CHECK
# =========================
def check_args():
    if len(sys.argv) != 2:
        print("ERROR: Must supply port number \nUSAGE: py dfs4.py <port>")
        sys.exit()
    try:
        port = int(sys.argv[1])
        return port
    except ValueError:
        print("ERROR: Port number must be a number.")
        sys.exit()


server_port = check_args()

# =========================
# AUTH PARAMETERS
# =========================
def auth_params():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_file = os.path.join(BASE_DIR, 'DFC', 'dfc.conf')

    if not os.path.exists(config_file):
        print(f"ERROR: {config_file} not found")
        sys.exit(1)

    auth = {}
    with open(config_file, 'r', encoding='cp1252') as f:
        lines = f.readlines()

    for i in range(0, len(lines), 2):
        user = lines[i].split()[1]
        pwd = lines[i + 1].split()[1]
        auth[user] = pwd

    return auth

auth_dict = auth_params()

# =========================
# CLIENT AUTH
# =========================
def client_auth(conn):
    username = conn.recv(2048).decode().strip()
    password = conn.recv(2048).decode().strip()

    if username in auth_dict and auth_dict[username] == password:
        conn.send(b"OK")
        print("Authorization Granted.")
        return username

    conn.send(b"ERROR")
    return None

# =========================
# CREATE USER DIRECTORY
# =========================
def new_dir(username):
    user_dir = os.path.join(STORAGE_ROOT, username)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

# =========================
# PUT FILE
# =========================
def put(conn, user_dir):
    buffersize = int(conn.recv(2048).decode())

    name1 = conn.recv(1024).decode()
    chunk1 = conn.recv(buffersize)

    base_name = name1.rsplit('.', 1)[0]
    folder_path = os.path.join(user_dir, base_name)
    os.makedirs(folder_path, exist_ok=True)

    with open(os.path.join(folder_path, name1), 'wb') as f:
        f.write(chunk1)

    name2 = conn.recv(1024).decode()
    chunk2 = conn.recv(buffersize)

    with open(os.path.join(folder_path, name2), 'wb') as f:
        f.write(chunk2)

# =========================
# LIST FILES (FIXED)
# =========================
def list_files(conn, user_dir):
    """
    Returns logical filenames only (no chunks)
    """
    logical_files = set()

    for root, dirs, files in os.walk(user_dir):
        for file in files:
            base = file.rsplit('.', 1)[0]
            logical_files.add(base)

    conn.send(pickle.dumps(sorted(logical_files)))

# =========================
# GET FILE
# =========================
def get(conn, user_dir):
    filename = conn.recv(1024).decode().strip()
    found_chunks = []

    for root, dirs, files in os.walk(user_dir):
        for file in files:
            if file.startswith(filename + "."):
                found_chunks.append(os.path.join(root, file))

    conn.send(pickle.dumps(found_chunks))

    for chunk_path in found_chunks:
        with open(chunk_path, 'rb') as f:
            conn.sendall(f.read())
            time.sleep(0.05)

# =========================
# SERVER LOOP
# =========================
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("0.0.0.0", server_port))
server_socket.listen(5)

print(f"DFS3 running on port {server_port}")
print(f"Storage root: {STORAGE_ROOT}")

while True:
    conn, addr = server_socket.accept()
    print("Client connected from", addr)

    try:
        username = client_auth(conn)
        if not username:
            conn.close()
            continue

        user_dir = new_dir(username)

        command = conn.recv(1024).decode().strip().upper()

        if command == "PUT":
            put(conn, user_dir)
        elif command == "LIST":
            list_files(conn, user_dir)
        elif command == "GET":
            get(conn, user_dir)
        else:
            conn.send(b"ERROR")

    except Exception as e:
        print("Error:", e)

    finally:
        conn.close()
