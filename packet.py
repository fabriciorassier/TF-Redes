"""
SRTP packet encoding/decoding and CRC32 checksum.

Header layout (9 bytes):
  Bits  0     : SYN
  Bits  1     : FIN
  Bits  2-15  : SEQ (14 bits)
  Bits  16    : ACK flag
  Bits  17    : NACK flag
  Bits  18-31 : ACK (14 bits)
  Bits  32-39 : Length (8 bits)
  Bits  40-71 : CRC32 (32 bits)
"""

import struct
import zlib

HEADER_SIZE = 9
MAX_PAYLOAD = 255
SEQ_MOD = 1 << 14  # 16384


def pack_header(syn, fin, seq, ack_flag, nack, ack, length, crc=0):
    word1 = ((syn & 1) << 15) | ((fin & 1) << 14) | (seq & 0x3FFF)
    word2 = ((ack_flag & 1) << 15) | ((nack & 1) << 14) | (ack & 0x3FFF)
    return struct.pack("!HHBI", word1, word2, length, crc & 0xFFFFFFFF)


def unpack_header(data):
    word1, word2, length, crc = struct.unpack("!HHBI", data[:HEADER_SIZE])
    syn = (word1 >> 15) & 1
    fin = (word1 >> 14) & 1
    seq = word1 & 0x3FFF
    ack_flag = (word2 >> 15) & 1
    nack = (word2 >> 14) & 1
    ack = word2 & 0x3FFF
    return syn, fin, seq, ack_flag, nack, ack, length, crc


def compute_crc(header_no_crc, payload=b""):
    return zlib.crc32(header_no_crc + payload) & 0xFFFFFFFF


def make_packet(syn=0, fin=0, seq=0, ack_flag=0, nack=0, ack=0, length=0, payload=b""):
    header_no_crc = pack_header(syn, fin, seq, ack_flag, nack, ack, length, crc=0)
    crc = compute_crc(header_no_crc, payload)
    header = pack_header(syn, fin, seq, ack_flag, nack, ack, length, crc=crc)
    return header + payload


def parse_packet(data):
    """Returns (syn, fin, seq, ack_flag, nack, ack, length, payload) or None if CRC invalid."""
    if len(data) < HEADER_SIZE:
        return None
    syn, fin, seq, ack_flag, nack, ack, length, received_crc = unpack_header(data)
    payload = data[HEADER_SIZE:]

    # Verify CRC: recompute with CRC field zeroed
    header_no_crc = pack_header(syn, fin, seq, ack_flag, nack, ack, length, crc=0)
    expected_crc = compute_crc(header_no_crc, payload)
    if (received_crc & 0xFFFFFFFF) != expected_crc:
        return None

    return syn, fin, seq, ack_flag, nack, ack, length, payload


def seq_add(seq, n):
    return (seq + n) % SEQ_MOD


def seq_lt(a, b):
    """True if a < b in circular sequence space."""
    half = SEQ_MOD // 2
    return ((b - a) % SEQ_MOD) < half and a != b


def seq_le(a, b):
    return a == b or seq_lt(a, b)
