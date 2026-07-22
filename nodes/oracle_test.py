"""Independent-oracle test: verifies EncodeFrame/DecodeFrame against a
from-scratch reference implementation that does NOT import canmatrix (or
this package's own _can_lib helpers) at all — plain int/bytes arithmetic
computing raw = round((phys - offset) / factor) and packing/unpacking
little-endian byte-aligned integers by hand. A round-trip through the same
library shows self-consistency, not correctness; this compares against math
worked out independently of the implementation under test.

Restricted to byte-aligned signals (start_bit % 8 == 0, length % 8 == 0),
where the little-endian byte order the DBC declares is unambiguous — the
same shape as EngineSpeed/EngineTemp in DBC_FIXTURE.
"""
from gen.messages_pb2 import CanDatabase, DecodeFrameInput, EncodeFrameInput
from nodes.decode_frame import decode_frame
from nodes.encode_frame import encode_frame
from nodes.testkit import DBC_FIXTURE, AxiomTestContext

DB = CanDatabase(content=DBC_FIXTURE, format="dbc")

# (signal, start_byte, length_bytes, factor, offset, is_signed, physical_value)
CASES = [
    ("EngineSpeed", 0, 2, 0.25, 0.0, False, 0.0),
    ("EngineSpeed", 0, 2, 0.25, 0.0, False, 1000.0),
    ("EngineSpeed", 0, 2, 0.25, 0.0, False, 16383.75),  # max
    ("EngineTemp", 2, 1, 1.0, -40.0, True, 25.0),
    ("EngineTemp", 2, 1, 1.0, -40.0, True, -40.0),  # min raw = 0
    ("EngineTemp", 2, 1, 1.0, -40.0, True, 87.0),
]


def _oracle_encode(start_byte, length_bytes, factor, offset, is_signed, physical_value):
    raw = round((physical_value - offset) / factor)
    payload = bytearray(8)
    payload[start_byte : start_byte + length_bytes] = raw.to_bytes(
        length_bytes, byteorder="little", signed=is_signed
    )
    return bytes(payload)


def _oracle_decode(data, start_byte, length_bytes, factor, offset, is_signed):
    raw = int.from_bytes(data[start_byte : start_byte + length_bytes], byteorder="little", signed=is_signed)
    return raw * factor + offset


def test_encode_frame_matches_independent_reference_implementation():
    ax = AxiomTestContext()
    for signal, start_byte, length_bytes, factor, offset, is_signed, value in CASES:
        expected = _oracle_encode(start_byte, length_bytes, factor, offset, is_signed, value)
        result = encode_frame(
            ax,
            EncodeFrameInput(database=DB, message_name="EngineData", frame_id=-1, signal_values={signal: value}),
        )
        assert result.error.code == "", (signal, value, result.error.message)
        assert bytes.fromhex(result.data_hex) == expected, (signal, value)


def test_decode_frame_matches_independent_reference_implementation():
    ax = AxiomTestContext()
    for signal, start_byte, length_bytes, factor, offset, is_signed, value in CASES:
        raw_bytes = _oracle_encode(start_byte, length_bytes, factor, offset, is_signed, value)
        expected_physical = _oracle_decode(raw_bytes, start_byte, length_bytes, factor, offset, is_signed)
        result = decode_frame(
            ax,
            DecodeFrameInput(
                database=DB, message_name="EngineData", frame_id=-1, data_hex=raw_bytes.hex()
            ),
        )
        assert result.error.code == ""
        assert abs(result.signal_values[signal] - expected_physical) < 1e-9, (signal, value)
