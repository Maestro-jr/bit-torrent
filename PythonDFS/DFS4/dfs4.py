#! /usr/bin/env python3

"""
Distributed File System
Server 4
Marcelo Sanches
Jan 2019
Modified: Fixed server root directory
"""

# modules
import os
import re
import sys
import time
import socket
import glob
import pickle

# ================= SERVER ROOT (DFS4) =================
SERVER_ROOT = r"C:\Users\HP\Desktop\Servers\Server 4"
os.makedirs(SERVER_ROOT, exist_ok=True)
os.chdir(SERVER_ROOT)
# ======================================================


# function to check port number assignment
def check_args():

    if len(sys.argv) != 2:
        print("ERROR: Must supply port number \nUSAGE: py dfs4.py 10004")
        sys.exit()

    try:
        if int(sys.argv[1]) != 10004:
            print("ERROR: Port number must be 10004")
            sys.exit()
        return int(sys.argv[1])
    except ValueError:
        print("ERROR: Port number must be a number.")
        sys.exit()

check_args()


# get authentication parameters
def auth_params():

    config_file = 'dfs.conf'

    with open(config_file, 'r', encoding='cp1252') as fh:
        users = re.findall(r'Username: .*', fh.read())

    with open(config_file, 'r', encoding='cp1252') as fh:
        passes = re.findall(r'Password: .*', fh.read())

    usernames = [u.split()[1] for u in users]
    passwords = [p.split()[1] for p in passes]

    global auth_dict
    auth_dict = dict(zip(usernames, passwords))
    return auth_dict


# authorize client
def client_auth(auth_dict, username, password):

    if username in auth_dict and auth_dict[username] == password:
        response = 'Authorization Granted.\n'
        print(response)
        conn.send(response.encode())
    else:
        response = 'Authorization Denied.\n'
        print(response)
        conn.send(response.encode())
        sys.exit()


# creates new directory for user
def new_dir(username):

    global new_dir_path
    new_dir_path = os.path.join(SERVER_ROOT, username)

    if not os.path.isdir(new_dir_path):
        os.makedirs(new_dir_path, exist_ok=True)
        print(f"Created user directory: {new_dir_path}")

    return new_dir_path


# PUT files
def put(new_dir_path):

    buffersize = int(conn.recv(2048).decode())
    print('Buffer size:', buffersize)

    name1 = conn.recv(1024).decode()
    chunk1 = conn.recv(buffersize).decode()
    print('Receiving', name1)

    file_folder = name1.split('_')[0]
    folder_path = os.path.join(new_dir_path, file_folder)
    os.makedirs(folder_path, exist_ok=True)

    with open(os.path.join(folder_path, name1), 'w') as fh:
        fh.write(chunk1)

    conn.send(b'Chunk 1 successfully transferred.\n')

    name2 = conn.recv(1024).decode()
    chunk2 = conn.recv(buffersize).decode()
    print('Receiving', name2)

    with open(os.path.join(folder_path, name2), 'w') as fh:
        fh.write(chunk2)

    conn.send(b'Chunk 2 successfully transferred.\n')
    sys.exit()


# LIST files
def list_files(username):

    user_dir = os.path.join(SERVER_ROOT, username)

    if not os.path.exists(user_dir):
        conn.send(b'There are no files yet.')
        return

    folders = next(os.walk(user_dir))[1]
    if not folders:
        conn.send(b'There are no files yet.')
        return

    filenames = []
    for folder in folders:
        filenames.extend(os.listdir(os.path.join(user_dir, folder)))

    if not filenames:
        conn.send(b'There are no files yet.')
        return

    with open('filenames.txt', 'w') as fh:
        for f in filenames:
            fh.write(f + '\n')

    with open('filenames.txt', 'rb') as fh:
        conn.send(fh.read())

    os.remove('filenames.txt')


# GET files
def get(username):

    filename = conn.recv(1024).decode()
    user_dir = os.path.join(SERVER_ROOT, username)
    file_dir = os.path.join(user_dir, filename)

    if not os.path.isdir(file_dir):
        conn.send(b'No such file exists.\n')
        sys.exit()

    chunks = os.listdir(file_dir)
    name1, name2 = chunks

    chunk1_path = os.path.join(file_dir, name1)
    chunk2_path = os.path.join(file_dir, name2)

    buffersize = os.stat(chunk1_path).st_size + 4
    conn.send(str(buffersize).encode())
    time.sleep(1)

    conn.send(name1.encode())
    time.sleep(0.5)
    conn.send(open(chunk1_path, 'rb').read())

    status = conn.recv(1024).decode()
    if status == 'Transfer incomplete':
        conn.send(name2.encode())
        time.sleep(0.5)
        conn.send(open(chunk2_path, 'rb').read())
        conn.recv(1024)

    sys.exit()


# ================= RUN SERVER =================

server_name = '127.0.0.1'
server_port = int(sys.argv[1])

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((server_name, server_port))
server_socket.listen(5)

print('DFS4 listening on port', server_port)
print('Serving directory:', SERVER_ROOT)

while True:
    conn, addr = server_socket.accept()
    print('Client connected.')

    username = conn.recv(2048).decode()
    password = conn.recv(2048).decode()

    auth_params()
    client_auth(auth_dict, username, password)

    new_dir(username)

    command = conn.recv(1024).decode()

    if command == 'put':
        put(new_dir_path)
    elif command == 'list':
        list_files(username)
        answer = conn.recv(1024).decode()
        if answer == 'get':
            get(username)
        elif answer == 'put':
            put(new_dir_path)
    elif command == 'get':
        get(username)
    else:
        sys.exit()

conn.close()
