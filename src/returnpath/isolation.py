"""Process-level guard for local execution, including subprocess entry points."""
import ipaddress
import socket


def install():
    original = socket.socket.connect
    original_ex = socket.socket.connect_ex

    def allowed(address):
        if not isinstance(address, tuple):
            return
        host = address[0]
        if host == "localhost":
            return
        try:
            valid = ipaddress.ip_address(host).is_loopback
        except ValueError:
            valid = False
        if not valid:
            raise PermissionError("Local mode prohibits non-loopback network access")

    def connect(sock, address):
        allowed(address)
        return original(sock, address)

    def connect_ex(sock, address):
        allowed(address)
        return original_ex(sock, address)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
