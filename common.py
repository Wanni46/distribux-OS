import json

AUTH_TOKEN = "distribux_secure_key"

def send(sock, msg):
    sock.sendall(json.dumps(msg).encode())

def receive(sock):
    return json.loads(sock.recv(1024).decode())

def authenticate(msg):
    return msg.get("token") == AUTH_TOKEN
