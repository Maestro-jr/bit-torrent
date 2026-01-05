#! /usr/bin/env python3

"""
Distributed File System
Server 1
Marcelo Sanches
Jan 2019
(MODIFIED: Fixed absolute storage root)
"""

# ========================
# MODULES
# ========================
import os
import re
import sys
import time
import socket
import glob
import pickle

# ========================
# STORAGE ROOT (SERVER 1)
# ========================
STORAGE_ROOT = r"C:\Users\HP\Desktop\Servers\Server 1"

# ========================
# ARGUMENT CHECK
# ========================
def check_args():
	if len(sys.argv) != 2:
		print("ERROR: Must supply port number")
		print("USAGE: python dfs1.py <port>")
		sys.exit(1)

# ========================
# CREATE USER DIRECTORY
# ========================
def new_dir(username):
	global new_dir_path
	new_dir_path = os.path.join(STORAGE_ROOT, username)

	if not os.path.isdir(new_dir_path):
		try:
			os.makedirs(new_dir_path, exist_ok=True)
			print(f"Successfully created directory {new_dir_path}")
		except OSError:
			print(f"Creation of directory {new_dir_path} failed")

	return new_dir_path

# ========================
# PUT FILE
# ========================
def put(conn, data, username):
	file_folder = data[1]
	chunk1_name = data[2]
	chunk2_name = data[3]

	user_dir = new_dir(username)
	new_folder_path = os.path.join(user_dir, file_folder)

	if not os.path.isdir(new_folder_path):
		os.makedirs(new_folder_path, exist_ok=True)

	print("Receiving chunk:", chunk1_name)
	chunk1 = conn.recv(1024 * 1024)
	with open(os.path.join(new_folder_path, chunk1_name), 'wb') as f:
		f.write(chunk1)

	print("Receiving chunk:", chunk2_name)
	chunk2 = conn.recv(1024 * 1024)
	with open(os.path.join(new_folder_path, chunk2_name), 'wb') as f:
		f.write(chunk2)

	print("PUT complete")

# ========================
# LIST FILES
# ========================
def list_files(conn, username):
	user_dir = os.path.join(STORAGE_ROOT, username)

	if not os.path.isdir(user_dir):
		conn.send(b"No files found")
		return

	files = os.listdir(user_dir)
	conn.send(pickle.dumps(files))

# ========================
# GET FILE
# ========================
def get(conn, data, username):
	filename = data[1]
	user_dir = os.path.join(STORAGE_ROOT, username)

	if not os.path.isdir(user_dir):
		conn.send(b"ERROR: User directory not found")
		return

	found_chunks = []

	for root, dirs, files in os.walk(user_dir):
		for file in files:
			if filename in file:
				found_chunks.append(os.path.join(root, file))

	if len(found_chunks) == 0:
		conn.send(b"ERROR: File not found")
		return

	conn.send(pickle.dumps(found_chunks))

	for chunk_path in found_chunks:
		with open(chunk_path, 'rb') as f:
			data = f.read()
			conn.send(data)
			time.sleep(0.1)

	print("GET complete")

# ========================
# AUTHENTICATION
# ========================
def authenticate(conn):
	auth = conn.recv(1024).decode().strip()
	try:
		username, password = auth.split()
	except ValueError:
		conn.send(b"ERROR")
		return None

	with open("dfs.conf", "r") as f:
		for line in f:
			user, pwd = line.split()
			if user == username and pwd == password:
				conn.send(b"OK")
				return username

	conn.send(b"ERROR")
	return None

# ========================
# MAIN SERVER LOOP
# ========================
def main():
	check_args()
	port = int(sys.argv[1])

	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.bind(("0.0.0.0", port))
	server.listen(5)

	print(f"DFS1 running on port {port}")
	print(f"Storage root: {STORAGE_ROOT}")

	while True:
		conn, addr = server.accept()
		print("Connection from", addr)

		username = authenticate(conn)
		if not username:
			conn.close()
			continue

		data = conn.recv(1024).decode().split()

		if not data:
			conn.close()
			continue

		command = data[0].upper()

		if command == "PUT":
			put(conn, data, username)
		elif command == "LIST":
			list_files(conn, username)
		elif command == "GET":
			get(conn, data, username)
		else:
			conn.send(b"ERROR: Invalid command")

		conn.close()

# ========================
# ENTRY POINT
# ========================
if __name__ == "__main__":
	main()
