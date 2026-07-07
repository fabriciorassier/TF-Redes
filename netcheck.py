"""
netcheck.py — Testa se a rede permite o SRTP rodar entre duas maquinas.

Usa o MESMO modelo de portas do SRTP:
  - Dados/PING vao para a porta P.
  - Respostas/ACK voltam para a porta P+1.

Se este teste passar, o SRTP tem tudo que precisa da rede.
Se falhar, o problema e firewall ou isolamento de clientes (nao o codigo).

Uso:
  Receiver (rode primeiro):   python3 netcheck.py --listen --port 6000
  Sender:                     python3 netcheck.py --host <IP-do-receiver> --port 6000
"""

import argparse
import socket
import sys
import time


def run_listen(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", port))
    print(f"[NETCHECK receiver] Escutando UDP na porta {port}. Aguardando PING...")
    print("  (Ctrl+C para sair)")
    while True:
        data, addr = s.recvfrom(2048)
        sender_ip = addr[0]
        print(f"[NETCHECK receiver] Recebi '{data.decode(errors='replace')}' de {addr}")
        reply_to = (sender_ip, port + 1)
        s.sendto(b"PONG", reply_to)
        print(f"[NETCHECK receiver] Respondi PONG para {reply_to}")


def run_send(host, port, retries=10):
    sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_reply = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_reply.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock_reply.bind(("", port + 1))
    sock_reply.settimeout(1.0)

    print(f"[NETCHECK sender] Enviando PING para {host}:{port}, aguardando PONG em {port + 1}")
    for attempt in range(1, retries + 1):
        sock_send.sendto(b"PING", (host, port))
        print(f"  tentativa {attempt}/{retries}: PING enviado...")
        try:
            data, addr = sock_reply.recvfrom(2048)
            print(f"\n  ==> SUCESSO! Recebi '{data.decode(errors='replace')}' de {addr}")
            print("  A rede permite o SRTP (portas P e P+1 funcionam nos dois sentidos).")
            return True
        except socket.timeout:
            continue
        except ConnectionResetError:
            # Windows manda ICMP port-unreachable quando P+1 ainda nao respondeu; ignore.
            continue

    print("\n  ==> FALHA: nenhum PONG recebido.")
    print("  Causas provaveis (nesta ordem):")
    print("   1. Isolamento de clientes no WiFi/hotspot (comum em hotspot de celular).")
    print("   2. Firewall bloqueando UDP de entrada na outra maquina (Windows Defender).")
    print("   3. IP do --host errado, ou receiver nao esta rodando.")
    return False


def main():
    p = argparse.ArgumentParser(description="Testa conectividade UDP no modelo de portas do SRTP")
    p.add_argument("--listen", action="store_true", help="Modo receiver")
    p.add_argument("--host", default="127.0.0.1", help="IP do receiver (modo sender)")
    p.add_argument("--port", type=int, required=True, help="Porta P")
    args = p.parse_args()

    if args.listen:
        run_listen(args.port)
    else:
        ok = run_send(args.host, args.port)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
