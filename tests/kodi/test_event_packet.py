"""The event-server packet is the Kodi layout, without a running Kodi."""

import struct

from event_client import ACTION_EXECBUILTIN, PT_ACTION, PT_BYE, PT_HELO, packets_for_builtin

_BUILTIN = "RunScript(script.angelstudios.integration-testing,captions,abc)"


def test_three_packets_in_order():
    packets = packets_for_builtin(_BUILTIN, uid=7)
    assert len(packets) == 3
    assert [_type(packet) for packet in packets] == [PT_HELO, PT_ACTION, PT_BYE]


def test_action_packet_carries_the_builtin():
    action = packets_for_builtin(_BUILTIN, uid=7)[1]
    assert action[:4] == b"XBMC"
    assert action[4:6] == b"\x02\x00"
    assert struct.unpack(">H", action[16:18])[0] == len(action) - 32
    assert struct.unpack(">I", action[18:22])[0] == 7
    payload = action[32:]
    assert payload[0] == ACTION_EXECBUILTIN
    assert _BUILTIN.encode("utf-8") in payload
    assert payload.endswith(b"\x00")


def _type(packet):
    return struct.unpack(">H", packet[6:8])[0]
