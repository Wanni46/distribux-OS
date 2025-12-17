import socket
import threading
import time
from common import send, receive, AUTH_TOKEN
from scheduler import select_node, detect_work_steal

# ---------------- GLOBAL STATE ----------------
nodes = {}          # node_id -> socket
node_status = {}    # node_id -> last heartbeat time
inbox = {}          # node_id -> list of messages (STATUS, DONE, etc.)
tasks = {}          # task_id -> node_id
task_id = 0
leader = None
dfs = {}

# ---------------- SINGLE RECEIVER PER NODE ----------------
def receiver(nid, sock):
    """
    One receiver thread per node.
    Reads ALL messages from socket and demultiplexes them.
    """
    while True:
        try:
            msg = receive(sock)
            msg_type = msg.get("type")

            if msg_type == "HEARTBEAT":
                node_status[nid] = time.time()
            else:
                # STATUS / DONE / others go to inbox
                inbox[nid].append(msg)

        except:
            # Socket closed or node crashed
            break


# ---------------- ALIVE NODES ----------------
def alive_nodes():
    now = time.time()
    return [i for i, t in node_status.items() if now - t < 5]


# ---------------- LEADER ELECTION (BULLY) ----------------
def elect_leader():
    global leader
    alive = alive_nodes()
    leader = max(alive) if alive else None
    print(f"[Leader Election] Leader is Node {leader}")


# ---------------- COLLECT STATUS SAFELY ----------------
def collect_status():
    """
    Send STATUS request to all alive nodes.
    Read replies from inbox (NOT sockets).
    """
    status = []

    for i in alive_nodes():
        try:
            send(nodes[i], {"type": "STATUS"})
        except:
            continue

    timeout = time.time() + 2
    expected = len(alive_nodes())

    while time.time() < timeout and len(status) < expected:
        for i in list(inbox.keys()):
            if inbox[i]:
                msg = inbox[i].pop(0)
                if msg.get("type") == "STATUS":
                    status.append(msg)

        time.sleep(0.05)

    return status


# ---------------- TASK RE-ROUTING ----------------
def reroute_tasks(failed_node):
    for tid, nid in list(tasks.items()):
        if nid == failed_node:
            print(f"[Recovery] Re-routing Task {tid}")
            status = collect_status()
            if status:
                node = select_node(status)
                try:
                    send(nodes[node["node"]], {"type": "TASK"})
                    tasks[tid] = node["node"]
                except:
                    pass


# ---------------- CONNECT TO NODES ----------------
for i in [1, 2, 3]:
    s = socket.socket()
    s.connect(("localhost", 5000 + i))

    # Authentication
    send(s, {"token": AUTH_TOKEN})

    nodes[i] = s
    inbox[i] = []
    node_status[i] = time.time()

    threading.Thread(
        target=receiver,
        args=(i, s),
        daemon=True
    ).start()

elect_leader()

print("\nDistribuX OS Controller CLI")
print("Commands:")
print(" status")
print(" submit_task")
print(" put_log <filename>")
print(" fail <node_id>")
print(" exit\n")


# ---------------- CLI LOOP ----------------
while True:
    cmd = input("DistribuX> ").split()
    if not cmd:
        continue

    # ---------- STATUS ----------
    if cmd[0] == "status":
        status = collect_status()
        if not status:
            print("No alive nodes")
        for st in status:
            print(st)

    # ---------- SUBMIT TASK ----------
    elif cmd[0] == "submit_task":
        task_id += 1
        status = collect_status()

        if not status:
            print("No alive nodes available")
            continue

        node = select_node(status)

        try:
            send(nodes[node["node"]], {"type": "TASK"})
            tasks[task_id] = node["node"]
            print(f"Task {task_id} assigned to Node {node['node']}")
        except:
            print("Task submission failed")

        busy, idle = detect_work_steal(status)
        if busy and idle:
            print(f"[Work Stealing] Possible between Node {busy} and Node {idle}")

    # ---------- DFS PUT ----------
    elif cmd[0] == "put_log" and len(cmd) == 2:
        dfs[cmd[1]] = alive_nodes()
        print(f"[DFS] {cmd[1]} replicated on nodes {dfs[cmd[1]]}")

    # ---------- FAIL NODE ----------
    elif cmd[0] == "fail" and len(cmd) == 2:
        nid = int(cmd[1])

        try:
            send(nodes[nid], {"type": "FAIL"})
        except:
            print(f"[INFO] Node {nid} already disconnected")

        print(f"Node {nid} marked as failed")

        # Remove node safely
        nodes.pop(nid, None)
        inbox.pop(nid, None)
        node_status.pop(nid, None)

        time.sleep(1)
        elect_leader()
        reroute_tasks(nid)

    # ---------- EXIT ----------
    elif cmd[0] == "exit":
        print("Shutting down DistribuX OS...")
        break

    else:
        print("Invalid command")
