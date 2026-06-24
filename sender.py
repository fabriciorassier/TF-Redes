"""
SRTP sender — Stop-and-Wait, Go-Back-N, Selective Repeat.
"""

import socket
import time
from packet import make_packet, parse_packet, MAX_PAYLOAD, HEADER_SIZE, seq_add, seq_lt, seq_le
from connection import handshake_active, teardown_active, TIMEOUT

# ---------------------------------------------------------------------------
# Stats helper
# ---------------------------------------------------------------------------

class Stats:
    def __init__(self):
        self.sent = 0
        self.retransmissions = 0
        self.start_time = None
        self.bytes_data = 0

    def start(self):
        self.start_time = time.time()

    def elapsed(self):
        return time.time() - self.start_time

    def throughput(self):
        elapsed = self.elapsed()
        return self.bytes_data / elapsed if elapsed > 0 else 0

    def report(self):
        print(f"[STATS] sent={self.sent} retransmissions={self.retransmissions} "
              f"elapsed={self.elapsed():.3f}s throughput={self.throughput()/1024:.2f} KB/s")


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------

def _chunk_file(data):
    """Yields (payload, length) tuples per the SRTP length semantics."""
    for i in range(0, len(data), MAX_PAYLOAD):
        chunk = data[i:i + MAX_PAYLOAD]
        yield chunk, len(chunk)


# ---------------------------------------------------------------------------
# Stop-and-Wait
# ---------------------------------------------------------------------------

def send_saw(sock_data, sock_ack, peer_addr, ack_port, file_data, stats):
    """Stop-and-Wait sender."""
    chunks = list(_chunk_file(file_data))
    seq = 0

    for idx, (payload, length) in enumerate(chunks):
        pkt = make_packet(seq=seq, length=length, payload=payload)
        stats.bytes_data += length

        while True:
            sock_data.sendto(pkt, peer_addr)
            stats.sent += 1

            sock_ack.settimeout(TIMEOUT)
            try:
                data, _ = sock_ack.recvfrom(HEADER_SIZE + MAX_PAYLOAD)
            except socket.timeout:
                stats.retransmissions += 1
                continue

            parsed = parse_packet(data)
            if parsed is None:
                stats.retransmissions += 1
                continue

            _, _, _, ack_flag, nack, ack_num, _, _ = parsed
            if ack_flag == 1 and ack_num == seq:
                break
            # Wrong ACK or NACK — retransmit
            stats.retransmissions += 1

        seq = (seq + 1) % (1 << 14)


# ---------------------------------------------------------------------------
# Go-Back-N
# ---------------------------------------------------------------------------

def send_gbn(sock_data, sock_ack, peer_addr, ack_port, file_data, window_size, stats):
    """Go-Back-N sender."""
    chunks = list(_chunk_file(file_data))
    total = len(chunks)
    base = 0       # oldest unacknowledged packet index
    next_seq_idx = 0  # next packet to send (index into chunks)
    seq_base = 0   # SEQ number of base

    # pre-build packets
    packets = []
    seq = 0
    for payload, length in chunks:
        packets.append((make_packet(seq=seq, length=length, payload=payload), length))
        stats.bytes_data += length
        seq = (seq + 1) % (1 << 14)

    send_times = {}  # base_idx -> time of last send
    sock_ack.settimeout(0.01)

    while base < total:
        # Send packets within window
        while next_seq_idx < total and next_seq_idx < base + window_size:
            pkt, _ = packets[next_seq_idx]
            sock_data.sendto(pkt, peer_addr)
            stats.sent += 1
            if next_seq_idx == base:
                send_times[base] = time.time()
            next_seq_idx += 1

        # Try to receive ACK
        try:
            data, _ = sock_ack.recvfrom(HEADER_SIZE + MAX_PAYLOAD)
            parsed = parse_packet(data)
            if parsed is not None:
                _, _, _, ack_flag, nack_flag, ack_num, _, _ = parsed
                if ack_flag == 1:
                    # Cumulative ACK: advance base to ack_num+1
                    ack_idx = ack_num  # SEQ == index since seq starts at 0
                    # Handle wrap-around: find actual index
                    new_base = _seq_to_idx(ack_num, base, window_size, total)
                    if new_base is not None and new_base >= base:
                        base = new_base + 1
                        seq_base = (ack_num + 1) % (1 << 14)
                        send_times[base] = time.time()
                elif nack_flag == 1:
                    # Retransmit from base
                    next_seq_idx = base
                    stats.retransmissions += (next_seq_idx - base)
        except socket.timeout:
            pass

        # Check timeout on base packet
        if base in send_times and (time.time() - send_times[base]) > TIMEOUT:
            next_seq_idx = base
            send_times[base] = time.time()
            stats.retransmissions += min(window_size, total - base)


def _seq_to_idx(seq_num, base, window_size, total):
    """Convert SEQ number to chunk index, searching within [base, base+window_size)."""
    for i in range(base, min(base + window_size, total)):
        if i % (1 << 14) == seq_num:
            return i
    return None


# ---------------------------------------------------------------------------
# Selective Repeat
# ---------------------------------------------------------------------------

def send_sr(sock_data, sock_ack, peer_addr, ack_port, file_data, window_size, stats):
    """Selective Repeat sender."""
    chunks = list(_chunk_file(file_data))
    total = len(chunks)

    packets = []
    seq = 0
    for payload, length in chunks:
        packets.append((make_packet(seq=seq, length=length, payload=payload), length))
        stats.bytes_data += length
        seq = (seq + 1) % (1 << 14)

    acked = [False] * total
    send_times = [None] * total
    base = 0
    next_idx = 0

    sock_ack.settimeout(0.01)

    while base < total:
        # Send new packets within window
        while next_idx < total and next_idx < base + window_size:
            if not acked[next_idx]:
                pkt, _ = packets[next_idx]
                sock_data.sendto(pkt, peer_addr)
                stats.sent += 1
                send_times[next_idx] = time.time()
            next_idx += 1

        # Try to receive ACK/NACK
        try:
            data, _ = sock_ack.recvfrom(HEADER_SIZE + MAX_PAYLOAD)
            parsed = parse_packet(data)
            if parsed is not None:
                _, _, _, ack_flag, nack_flag, ack_num, _, _ = parsed
                if ack_flag == 1 and not nack_flag:
                    idx = _seq_to_idx(ack_num, base, window_size, total)
                    if idx is not None:
                        acked[idx] = True
                elif nack_flag == 1:
                    idx = _seq_to_idx(ack_num, base, window_size, total)
                    if idx is not None and not acked[idx]:
                        pkt, _ = packets[idx]
                        sock_data.sendto(pkt, peer_addr)
                        stats.sent += 1
                        stats.retransmissions += 1
                        send_times[idx] = time.time()
        except socket.timeout:
            pass

        # Advance base over contiguous ACKs
        while base < total and acked[base]:
            base += 1

        # Timeout check: retransmit individual unacknowledged packets
        now = time.time()
        for i in range(base, min(base + window_size, total)):
            if not acked[i] and send_times[i] and (now - send_times[i]) > TIMEOUT:
                pkt, _ = packets[i]
                sock_data.sendto(pkt, peer_addr)
                stats.sent += 1
                stats.retransmissions += 1
                send_times[i] = now


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_sender(host, port, filepath, mode, window):
    with open(filepath, "rb") as f:
        file_data = f.read()

    sock_data = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_ack = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_ack.bind(("", port + 1))

    try:
        print(f"[SENDER] Connecting to {host}:{port}, mode={mode}, window={window}")
        negotiated_window, peer_addr = handshake_active(sock_data, sock_ack, host, port, window)
        print(f"[SENDER] Handshake complete. Negotiated window={negotiated_window}")

        stats = Stats()
        stats.start()

        if mode == "saw":
            send_saw(sock_data, sock_ack, peer_addr, port + 1, file_data, stats)
        elif mode == "gbn":
            send_gbn(sock_data, sock_ack, peer_addr, port + 1, file_data, negotiated_window, stats)
        elif mode == "sr":
            send_sr(sock_data, sock_ack, peer_addr, port + 1, file_data, negotiated_window, stats)

        teardown_active(sock_data, peer_addr)
        print("[SENDER] Transfer complete.")
        stats.report()

    finally:
        sock_data.close()
        sock_ack.close()
