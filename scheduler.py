def select_node(status_list):
    # Accept ONLY valid STATUS messages
    valid = [
        n for n in status_list
        if isinstance(n, dict)
        and n.get("type") == "STATUS"
        and "alive" in n
        and "load" in n
    ]

    if not valid:
        raise Exception("No valid STATUS messages available")

    alive_nodes = [n for n in valid if n["alive"]]

    if not alive_nodes:
        raise Exception("No alive nodes available")

    return min(alive_nodes, key=lambda n: n["load"])


def detect_work_steal(status_list):
    valid = [
        n for n in status_list
        if n.get("type") == "STATUS" and n.get("alive")
    ]

    if len(valid) < 2:
        return None, None

    busy = max(valid, key=lambda n: n["load"])
    idle = min(valid, key=lambda n: n["load"])

    if busy["load"] - idle["load"] >= 2:
        return busy["node"], idle["node"]

    return None, None
