"""
SRTP receiver — Stop-and-Wait, Go-Back-N, Selective Repeat.
"""

import socket
import sys
import time
from packet import make_packet, parse_packet, MAX_PAYLOAD, HEADER_SIZE, seq_add
from connection import handshake_passive, teardown_passive, TIMEOUT


def _recvfrom_safe(sock, bufsize):
    """recvfrom that ignores Windows ICMP port-unreachable errors."""
    while True:
        try:
            return sock.recvfrom(bufsize)
        except ConnectionResetError:
            return None, None


# ---------------------------------------------------------------------------
# Stop-and-Wait
# ---------------------------------------------------------------------------

def recv_saw(sock, peer_addr, port, output_path):
    """
    Stop-and-Wait receiver.
    peer_addr: sender's (host, ephemeral) from handshake — we use peer_addr[0] + port+1 for ACKs.
    """
    ack_target = (peer_addr[0], port + 1)
    buffer = bytearray()
    expected_seq = 0
    sock.settimeout(TIMEOUT * 100)

    while True:
        try:
            data, addr = sock.recvfrom(HEADER_SIZE + MAX_PAYLOAD)
        except (socket.timeout, ConnectionResetError):
            print("[RECEIVER] Timeout waiting for data.")
            return

        parsed = parse_packet(data)
        if parsed is None:
            # CRC error — silent discard
            continue

        syn, fin, seq, ack_flag, nack, ack_num, length, payload = parsed

        if fin == 1:
            finack = make_packet(fin=1, ack_flag=1)
            sock.sendto(finack, ack_target)
            print("[RECEIVER] FIN received, connection closed.")
            break

        if seq != expected_seq:
            # Out of order — silent discard (SAW)
            continue

        buffer.extend(payload[:length])

        ack_pkt = make_packet(ack_flag=1, ack=seq)
        sock.sendto(ack_pkt, ack_target)

        expected_seq = (expected_seq + 1) % (1 << 14)

        if length < MAX_PAYLOAD:
            _write_output(output_path, buffer)
            print(f"[RECEIVER] File received ({len(buffer)} bytes) -> {output_path}")
            _wait_for_fin(sock, ack_target)
            break


# ---------------------------------------------------------------------------
# Go-Back-N
# ---------------------------------------------------------------------------

def recv_gbn(sock, peer_addr, port, output_path):
    """Go-Back-N receiver — accepts only in-order packets."""
    ack_target = (peer_addr[0], port + 1)
    buffer = bytearray()
    expected_seq = 0
    sock.settimeout(TIMEOUT * 100)

    while True:
        try:
            data, addr = sock.recvfrom(HEADER_SIZE + MAX_PAYLOAD)
        except (socket.timeout, ConnectionResetError):
            print("[RECEIVER] Timeout waiting for data.")
            return

        parsed = parse_packet(data)
        if parsed is None:
            continue

        syn, fin, seq, ack_flag, nack, ack_num, length, payload = parsed

        if fin == 1:
            finack = make_packet(fin=1, ack_flag=1)
            sock.sendto(finack, ack_target)
            print("[RECEIVER] FIN received.")
            break

        if seq == expected_seq:
            buffer.extend(payload[:length])
            ack_pkt = make_packet(ack_flag=1, ack=seq)
            sock.sendto(ack_pkt, ack_target)
            expected_seq = (expected_seq + 1) % (1 << 14)

            if length < MAX_PAYLOAD:
                _write_output(output_path, buffer)
                print(f"[RECEIVER] File received ({len(buffer)} bytes) -> {output_path}")
                _wait_for_fin(sock, ack_target)
                break
        else:
            nack_pkt = make_packet(ack_flag=1, nack=1, ack=expected_seq)
            sock.sendto(nack_pkt, ack_target)


# ---------------------------------------------------------------------------
# Selective Repeat
# ---------------------------------------------------------------------------

def recv_sr(sock, peer_addr, port, output_path, window_size):
    """Selective Repeat receiver — buffers out-of-order packets."""
    ack_target = (peer_addr[0], port + 1)
    recv_buffer = {}   # seq -> (payload, length)
    base_seq = 0
    assembled = bytearray()
    finished = False
    sock.settimeout(TIMEOUT * 100)

    while True:
        try:
            data, addr = sock.recvfrom(HEADER_SIZE + MAX_PAYLOAD)
        except (socket.timeout, ConnectionResetError):
            print("[RECEIVER] Timeout waiting for data.")
            return

        parsed = parse_packet(data)
        if parsed is None:
            continue

        syn, fin, seq, ack_flag, nack, ack_num, length, payload = parsed

        if fin == 1:
            finack = make_packet(fin=1, ack_flag=1)
            sock.sendto(finack, ack_target)
            print("[RECEIVER] FIN received.")
            break

        # Accept if within window [base_seq, base_seq + window_size)
        offset = (seq - base_seq) % (1 << 14)
        if offset < window_size:
            recv_buffer[seq] = (payload[:length], length)
            ack_pkt = make_packet(ack_flag=1, ack=seq)
            sock.sendto(ack_pkt, ack_target)

            while base_seq in recv_buffer:
                pl, ln = recv_buffer.pop(base_seq)
                assembled.extend(pl)
                if ln < MAX_PAYLOAD:
                    finished = True
                base_seq = (base_seq + 1) % (1 << 14)

            if finished:
                _write_output(output_path, assembled)
                print(f"[RECEIVER] File received ({len(assembled)} bytes) -> {output_path}")
                _wait_for_fin(sock, ack_target)
                break
        else:
            nack_pkt = make_packet(ack_flag=1, nack=1, ack=base_seq)
            sock.sendto(nack_pkt, ack_target)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_output(path, data):
    if path:
        with open(path, "wb") as f:
            f.write(data)


def _wait_for_fin(sock, ack_target):
    """After file received, wait for sender's FIN and reply FIN+ACK to ack_target."""
    sock.settimeout(TIMEOUT * 20)
    for _ in range(50):
        try:
            data, addr = sock.recvfrom(HEADER_SIZE + MAX_PAYLOAD)
        except (socket.timeout, ConnectionResetError):
            return
        parsed = parse_packet(data)
        if parsed is None:
            continue
        syn, fin, seq, ack_flag, nack, ack_num, length, payload = parsed
        if fin == 1:
            finack = make_packet(fin=1, ack_flag=1)
            sock.sendto(finack, ack_target)
            return


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_receiver(port, output_path, mode, window):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", port))

    try:
        print(f"[RECEIVER] Listening on port {port}, mode={mode}, window={window}")
        negotiated_window, peer_addr = handshake_passive(sock, window)
        print(f"[RECEIVER] Handshake complete with {peer_addr}. Negotiated window={negotiated_window}")

        if mode == "saw":
            recv_saw(sock, peer_addr, port, output_path)
        elif mode == "gbn":
            recv_gbn(sock, peer_addr, port, output_path)
        elif mode == "sr":
            recv_sr(sock, peer_addr, port, output_path, negotiated_window)

    finally:
        sock.close()
