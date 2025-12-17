import socket
import threading
import sys
import time
from common import send, receive, authenticate

if len(sys.argv) < 2:
    print("Usage: python node.py <node_id>")
    sys.exit(1)

NODE_ID = int(sys.argv[1])
PORT = 5000 + NODE_ID

load = 0
alive = True

def heartbeat(conn):
    while alive:
        try:
            send(conn, {"type": "HEARTBEAT", "node": NODE_ID})
            time.sleep(3)
        except:
            break

def handle_controller(conn):
    global load, alive

    # 🔐 Authentication
    auth_msg = receive(conn)
    if not authenticate(auth_msg):
        print("[SECURITY] Authentication failed")
        conn.close()
        return

    print(f"[Node {NODE_ID}] Authentication successful")

    threading.Thread(
        target=heartbeat,
        args=(conn,),
        daemon=True
    ).start()

    while alive:
        try:
            msg = receive(conn)
        except:
            break

        msg_type = msg.get("type")

        if msg_type == "TASK":
            load += 1
            print(f"[Node {NODE_ID}] Executing task")
            time.sleep(5)
            load -= 1
            send(conn, {"type": "DONE", "node": NODE_ID})

        elif msg_type == "STATUS":
            send(conn, {
                "type": "STATUS",
                "node": NODE_ID,
                "alive": alive,
                "load": load
            })

        elif msg_type == "FAIL":
            alive = False
            print(f"[Node {NODE_ID}] FAILED")

def start():
    s = socket.socket()
    s.bind(("localhost", PORT))
    s.listen(1)

    print(f"[Node {NODE_ID}] running on port {PORT}")
    conn, _ = s.accept()
    handle_controller(conn)

start()
