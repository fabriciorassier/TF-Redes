"""
SRTP — Simple Reliable Transport Protocol
Usage:
  Receiver: python srtp.py --listen --port 6000 [--output received.bin] [--mode saw|gbn|sr] [--window N]
  Sender:   python srtp.py --host 192.168.1.10 --port 6000 --file arquivo.bin [--mode saw|gbn|sr] [--window N]
"""

import argparse
import sys
from sender import run_sender
from receiver import run_receiver


def main():
    parser = argparse.ArgumentParser(description="SRTP - Simple Reliable Transport Protocol")
    parser.add_argument("--listen", action="store_true", help="Run in receiver (listen) mode")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Remote host (sender mode)")
    parser.add_argument("--port", type=int, required=True, help="Port P (receiver listens on P; sender sends to P, receives ACKs on P+1)")
    parser.add_argument("--file", type=str, help="File to send (sender mode)")
    parser.add_argument("--output", type=str, default="received_output.bin", help="Output file path (receiver mode)")
    parser.add_argument("--mode", choices=["saw", "gbn", "sr"], default="saw", help="Protocol mode: saw, gbn, sr")
    parser.add_argument("--window", type=int, default=4, help="Proposed window size (1-255, ignored for SAW)")

    args = parser.parse_args()

    window = max(1, min(255, args.window))

    if args.listen:
        run_receiver(args.port, args.output, args.mode, window)
    else:
        if not args.file:
            print("Error: --file is required in sender mode.", file=sys.stderr)
            sys.exit(1)
        run_sender(args.host, args.port, args.file, args.mode, window)


if __name__ == "__main__":
    main()
