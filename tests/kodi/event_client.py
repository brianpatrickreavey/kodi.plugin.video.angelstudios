"""Tell a running Kodi to run a builtin, over the event server on port 9777.

The packet layout is the one in Kodi's xbmcclient.py. Port 9777 accepts the
command. It does not send a result back.
"""

import socket
import struct
import time

PT_HELO = 0x01
PT_BYE = 0x02
PT_ACTION = 0x0A
ACTION_EXECBUILTIN = 0x01
ICON_NONE = 0x00


def packets_for_builtin(builtin, uid=1):
    """Return the HELO, ACTION, and BYE packets for one builtin call."""
    payloads = [
        (PT_HELO, _helo("Angel integration")),
        (PT_ACTION, _action(builtin)),
        (PT_BYE, b""),
    ]
    return [_packet(packet_type, payload, uid) for packet_type, payload in payloads]


def send_builtin(builtin, host="127.0.0.1", port=9777):
    """Send one builtin to Kodi. A closed port raises OSError."""
    uid = int(time.time()) & 0xFFFFFFFF
    packets = packets_for_builtin(builtin, uid)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for packet in packets:
            sock.sendto(packet, (host, port))
    finally:
        sock.close()


def _packet(packet_type, payload, uid):
    header = struct.pack(
        ">4sBBHIIHI10s",
        b"XBMC",
        2,
        0,
        packet_type,
        1,
        1,
        len(payload),
        uid,
        b"\x00" * 10,
    )
    return header + payload


def _helo(name):
    return _text(name) + bytes([ICON_NONE])


def _action(builtin):
    return bytes([ACTION_EXECBUILTIN]) + _text(builtin)


def _text(value):
    return value.encode("utf-8") + b"\x00"
