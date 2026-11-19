"""Адреса этого компьютера, по которым друг может открыть сайт."""
import socket

_CACHE = None


def _label(ip):
    if ip.startswith("26."):
        return "Radmin VPN"
    if ip.startswith("25."):
        return "Hamachi"
    return "Wi-Fi / локальная сеть"


def addresses():
    """[(адрес, подпись)] — основной адрес первым. Петля, link-local и VirtualBox пропускаются."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    found = []
    try:  # основной адрес: через какой интерфейс идёт маршрут наружу (пакет не отправляется)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.254.254.254", 1))
            found.append(s.getsockname()[0])
        finally:
            s.close()
    except OSError:
        pass
    try:
        found += [i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)]
    except OSError:
        pass
    seen, out = set(), []
    for ip in found:
        if ip in seen or ip.startswith(("127.", "169.254.", "0.", "192.168.56.")):
            continue
        seen.add(ip)
        out.append((ip, _label(ip)))
    _CACHE = out
    return out
