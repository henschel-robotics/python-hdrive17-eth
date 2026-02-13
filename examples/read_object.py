"""
Raw TCP terminal for reading HDrive17-ETH objects.
Works like telnet — sends the XML command and prints the raw response.

Usage:
    python read_object.py 4 19
    python read_object.py 4 17 --ip 192.168.122.102
"""

import argparse
import socket



def main():
    parser = argparse.ArgumentParser(description="Read an HDrive object (raw TCP)")
    parser.add_argument("index", type=int, help="Object index")
    parser.add_argument("subindex", type=int, help="Object sub-index")
    parser.add_argument("--ip", default="192.168.122.102", help="HDrive IP address")
    parser.add_argument("--port", type=int, default=1000, help="TCP port")
    args = parser.parse_args()

    xml = f'<objRead a="{args.index}" b="{args.subindex}" />'
    print(f">>> {xml}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.settimeout(3.0)
    sock.connect((args.ip, args.port))
    sock.sendall(xml.encode("ascii"))

    try:
        data = sock.recv(45)
        print(f"<<< {data.decode('ascii', errors='replace')}")
        print(f"    len: {len(data)} bytes")
    except socket.timeout:
        print("<<< (no response — timed out)")

    sock.close()


if __name__ == "__main__":
    main()
