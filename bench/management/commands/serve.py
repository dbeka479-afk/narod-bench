"""python manage.py serve [порт] — запуск сайта так, чтобы его мог открыть и друг.

Чем отличается от runserver:
* слушает сразу все адреса компьютера (IPv4 и IPv6): localhost, Wi-Fi, Radmin VPN, Live Share;
  runserver по умолчанию слушает только 127.0.0.1 — с другого компьютера туда не попасть;
* порт по умолчанию 8765: 8000 часто занят другими Django-проектами;
* на Windows не даёт второму серверу «тихо» занять тот же порт (иначе запросы уходят не в тот проект);
* печатает адреса, которые нужно дать другу.
"""
import socket
import sys

from django.contrib.staticfiles.management.commands.runserver import Command as RunserverCommand
from django.core.management.base import CommandError
from django.core.servers.basehttp import WSGIServer

from bench.net import addresses

PORT = 8765


def _prepare(sock):
    if sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    if sock.family == socket.AF_INET6:
        try:  # один сокет на IPv6 и IPv4 сразу
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, OSError):
            pass


class DualStackServer(WSGIServer):
    def __init__(self, *args, **kwargs):
        if sys.platform == "win32":
            kwargs["allow_reuse_address"] = False
        super().__init__(*args, **kwargs)

    def server_bind(self):
        _prepare(self.socket)
        super().server_bind()


class Command(RunserverCommand):
    help = f"Запустить сайт для себя и друга: все адреса компьютера, порт {PORT}."
    server_cls = DualStackServer

    def handle(self, *args, **options):
        ap = options.get("addrport") or ""
        if not ap:
            ap = f"[::]:{PORT}"
        elif ap.isdigit():
            ap = f"[::]:{ap}"
        options["addrport"] = ap
        host, _, port = ap.rpartition(":")
        self._check_port(host.strip("[]"), int(port))
        super().handle(*args, **options)

    def _check_port(self, host, port):
        fam = socket.AF_INET6 if ":" in host else socket.AF_INET
        s = socket.socket(fam, socket.SOCK_STREAM)
        try:
            _prepare(s)
            s.bind((host, port))
        except OSError:
            raise CommandError(
                f"Порт {port} уже занят — скорее всего, сайт уже запущен в другом окне "
                f"(или там работает другой проект). Закройте то окно или выберите другой порт: "
                f"python manage.py serve {port + 1}")
        finally:
            s.close()

    def on_bind(self, server_port):
        lines = ["", "  Народный бенчмарк запущен", "",
                 f"  {'Этот компьютер:':<28}http://localhost:{server_port}/"]
        if self.addr in ("::", "0.0.0.0", "0"):
            for ip, label in addresses():
                lines.append(f"  {label + ':':<28}http://{ip}:{server_port}/")
        lines += ["",
                  f"  Live Share: панель Live Share -> Shared Servers -> Share Server -> {server_port}.",
                  f"  Друг открывает у себя http://localhost:{server_port}/",
                  "",
                  "  Не закрывайте это окно, пока идёт сравнение. Остановить: Ctrl+C", ""]
        self.stdout.write("\n".join(lines))
        self.stdout.flush()
