import socket

def is_connected(host: str = "1.1.1.1", port: int = 53, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False  