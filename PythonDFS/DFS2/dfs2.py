#! /usr/bin/env python3

"""
Distributed File System
Server 2
Fonyuy Berka
Jan 2026
"""

# =========================
# MODULES
# =========================
import os
import re
import sys
import time
import socket

# =========================
# STORAGE ROOT (DFS2)
# =========================
STORAGE_ROOT = r"C:\Users\HP\Desktop\Servers\Server 2"

# =========================
# ARGUMENT CHECK
# =========================
def check_args():
	if len(sys.argv) != 2:
		print("ERROR: Must supply port number \nUSAGE: py dfs2.py 10002")
		sys.exit()

	try:
		if int(sys.argv[1]) != 10002:
			print("ERROR: Port number must be 10002")
			sys.exit()
		return int(sys.argv[1])
	except ValueError:
		print("ERROR: Port number must be a number.")
		sys.exit()

check_args()

# =========================
# AUTH PARAMETERS
# =========================
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

# =========================
# CLIENT AUTH
# =========================
def client_auth(auth_dict, username, password):
	if username in auth_dict and auth_dict[username] == password:
		conn.send(b"Authorization Granted.\n")
		print("Authorization Granted.")
		return

	conn.send(b"Authorization Denied.\n")
	sys.exit()

# =========================
# CREATE USER DIRECTORY
# =========================
def new_dir(username):
	global new_dir_path
	new_dir_path = os.path.join(STORAGE_ROOT, username)
	os.makedirs(new_dir_path, exist_ok=True)
	return new_dir_path

# =========================
# PUT FILE
# =========================
def put(new_dir_path):
	buffersize = int(conn.recv(2048).decode())
	print("Buffer size:", buffersize)

	# -------- First chunk --------
	name1 = conn.recv(1024).decode()
	chunk1 = conn.recv(buffersize)

	file_folder = name1.split('_')[0]
	file_dir = os.path.join(new_dir_path, file_folder)
	os.makedirs(file_dir, exist_ok=True)

	with open(os.path.join(file_dir, name1), 'wb') as fh:
		fh.write(chunk1)

	conn.send(b"Chunk 1 successfully transferred.\n")

	# -------- Second chunk --------
	name2 = conn.recv(1024).decode()
	chunk2 = conn.recv(buffersize)

	with open(os.path.join(file_dir, name2), 'wb') as fh:
		fh.write(chunk2)

	conn.send(b"Chunk 2 successfully transferred.\n")
	sys.exit()

# =========================
# LIST FILES
# =========================
def list_files(username):
	user_dir = os.path.join(STORAGE_ROOT, username)

	if not os.path.isdir(user_dir):
		conn.send(b"There are no files yet.")
		return

	file_dirs = next(os.walk(user_dir))[1]
	if not file_dirs:
		conn.send(b"There are no files yet.")
		return

	with open("filenames.txt", "w") as fh:
		for folder in file_dirs:
			for file in os.listdir(os.path.join(user_dir, folder)):
				fh.write(file + "\n")

	conn.send(open("filenames.txt", "rb").read())
	os.remove("filenames.txt")

# =========================
# GET FILE
# =========================
def get(username):
	filename = conn.recv(1024).decode()
	user_dir = os.path.join(STORAGE_ROOT, username)
	file_dir = os.path.join(user_dir, filename)

	if not os.path.isdir(file_dir):
		conn.send(b"No such file exists.\n")
		sys.exit()

	name1, name2 = os.listdir(file_dir)
	chunk1_path = os.path.join(file_dir, name1)
	chunk2_path = os.path.join(file_dir, name2)

	buffersize = os.path.getsize(chunk1_path) + 4
	conn.send(str(buffersize).encode())
	time.sleep(0.5)

	conn.send(name1.encode())
	time.sleep(0.5)
	conn.send(open(chunk1_path, "rb").read())

	FINACK = conn.recv(1024).decode()
	if FINACK == "Transfer incomplete":
		conn.send(name2.encode())
		time.sleep(0.5)
		conn.send(open(chunk2_path, "rb").read())

	sys.exit()

# =========================
# SERVER LOOP
# =========================
server_name = "127.0.0.1"
server_port = int(sys.argv[1])

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((server_name, server_port))
server_socket.listen(5)

print("DFS2 running on port 10002")
print("Storage root:", STORAGE_ROOT)

while True:
	conn, _ = server_socket.accept()
	print("Client connected")

	username = conn.recv(2048).decode()
	password = conn.recv(2048).decode()

	auth_params()
	client_auth(auth_dict, username, password)
	new_dir(username)

	command = conn.recv(1024).decode()

	if command == "put":
		put(new_dir_path)
	elif command == "list":
		list_files(username)
	elif command == "get":
		get(username)
	else:
		sys.exit()
