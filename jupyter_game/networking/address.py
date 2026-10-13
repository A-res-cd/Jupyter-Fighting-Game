"""LAN address discovery and direct-IP port."""
import socket

ONLINE_PORT = 50555


def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as temp:
            temp.settimeout(1)
            temp.connect(("8.8.8.8", 80))
            return temp.getsockname()[0]
    except Exception:
        return "127.0.0.1"


