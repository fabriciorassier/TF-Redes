"""
SRTP connection handshake and teardown helpers.

Port model:
  - Receiver listens on P.
  - Sender connects to P, then (after handshake) listens on P+1 for ACKs.
  - Receiver sends ACKs from P to P+1.
"""

import socket
import time
from packet import make_packet, parse_packet, HEADER_SIZE

TIMEOUT = 0.1  # 100 ms
MAX_RETRIES = 50


def _recv_parsed(sock, bufsize=HEADER_SIZE + 255):
    try:
        data, addr = sock.recvfrom(bufsize)
        pkt = parse_packet(data)
        return pkt, addr
    except socket.timeout:
        return None, None


def handshake_active(sock_send, sock_recv, host, port, window):
    """
    Sender side: send SYN, wait SYN+ACK, send ACK.
    Returns negotiated window size (min of both proposals).
    sock_send: socket used to send (bound to nothing special, sends to host:port)
    sock_recv: socket bound to port+1, used after handshake to receive ACKs
    """
    syn_pkt = make_packet(syn=1, length=window)

    for attempt in range(MAX_RETRIES):
        sock_send.sendto(syn_pkt, (host, port))
        sock_send.settimeout(TIMEOUT)
        try:
            data, addr = sock_send.recvfrom(HEADER_SIZE + 255)
        except (socket.timeout, ConnectionResetError):
            continue

        pkt = parse_packet(data)
        if pkt is None:
            continue
        syn, fin, seq, ack_flag, nack, ack, their_window, payload = pkt
        if syn == 1 and ack_flag == 1:
            negotiated = min(window, their_window)
            # Send ACK to confirm
            ack_pkt = make_packet(ack_flag=1, ack=0)
            sock_send.sendto(ack_pkt, addr)
            return negotiated, addr

    raise ConnectionError("Handshake failed: no SYN+ACK received")


def handshake_passive(sock, window):
    """
    Receiver side: wait for SYN, reply SYN+ACK, wait for ACK.
    Returns negotiated window size and sender address.
    """
    sock.settimeout(None)  # block until SYN arrives
    while True:
        data, addr = sock.recvfrom(HEADER_SIZE + 255)
        pkt = parse_packet(data)
        if pkt is None:
            continue
        syn, fin, seq, ack_flag, nack, ack, their_window, payload = pkt
        if syn == 1:
            negotiated = min(window, their_window)
            synack = make_packet(syn=1, ack_flag=1, ack=0, length=negotiated)
            sock.sendto(synack, addr)

            # Wait for the final ACK
            sock.settimeout(TIMEOUT * 5)
            for _ in range(MAX_RETRIES):
                try:
                    data2, addr2 = sock.recvfrom(HEADER_SIZE + 255)
                except (socket.timeout, ConnectionResetError):
                    sock.sendto(synack, addr)
                    continue
                pkt2 = parse_packet(data2)
                if pkt2 is None:
                    continue
                s2, f2, sq2, af2, nk2, ak2, ln2, pl2 = pkt2
                if af2 == 1 and s2 == 0:
                    return negotiated, addr
                # Re-sent SYN? resend SYN+ACK
                if s2 == 1:
                    sock.sendto(synack, addr)
            raise ConnectionError("Handshake failed: no final ACK")


def teardown_active(sock_send, sock_recv, peer_addr):
    """Sender sends FIN (via sock_send to peer), waits for FIN+ACK on sock_recv (P+1)."""
    fin_pkt = make_packet(fin=1, length=0)
    for _ in range(MAX_RETRIES):
        sock_send.sendto(fin_pkt, peer_addr)
        sock_recv.settimeout(TIMEOUT)
        try:
            data, _ = sock_recv.recvfrom(HEADER_SIZE + 255)
        except socket.timeout:
            continue
        pkt = parse_packet(data)
        if pkt is None:
            continue
        syn, fin, seq, ack_flag, nack, ack, length, payload = pkt
        if fin == 1 and ack_flag == 1:
            return
    raise ConnectionError("Teardown failed: no FIN+ACK")


def teardown_passive(sock, peer_addr):
    """Receiver waits for FIN, replies FIN+ACK."""
    sock.settimeout(TIMEOUT * 10)
    for _ in range(MAX_RETRIES):
        try:
            data, addr = sock.recvfrom(HEADER_SIZE + 255)
        except socket.timeout:
            return
        pkt = parse_packet(data)
        if pkt is None:
            continue
        syn, fin, seq, ack_flag, nack, ack, length, payload = pkt
        if fin == 1:
            finack = make_packet(fin=1, ack_flag=1)
            sock.sendto(finack, addr)
            return
