"""LAN URL discovery and QR-code display helpers."""

import ipaddress
import socket

import qrcode


PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)


def _is_rfc1918(ip: str) -> bool:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return isinstance(address, ipaddress.IPv4Address) and any(
        address in network for network in PRIVATE_NETWORKS
    )


def get_lan_ips() -> list[str]:
    ips: list[str] = []
    for target in ("8.8.8.8", "1.1.1.1"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect((target, 80))
            ip = sock.getsockname()[0]
            if _is_rfc1918(ip):
                ips.append(ip)
        except OSError:
            pass
        finally:
            sock.close()

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if _is_rfc1918(ip):
                ips.append(ip)
    except OSError:
        pass

    return list(dict.fromkeys(ips)) or ["127.0.0.1"]


def generate_and_display_qr(url: str) -> None:
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)

    print(f"Scan this QR code or open {url} on your iPhone:")
    qr.print_ascii(invert=True)
    try:
        qr.make_image(fill_color="black", back_color="white").show()
    except OSError as exc:
        print(f"Could not open QR image viewer: {exc}")
