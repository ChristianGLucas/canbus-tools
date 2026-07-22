from gen.messages_pb2 import CanDatabase, DecodeFrameInput
from nodes.decode_frame import decode_frame
from nodes.testkit import DBC_FIXTURE, AxiomTestContext

DB = CanDatabase(content=DBC_FIXTURE, format="dbc")


def test_decode_frame_by_name():
    ax = AxiomTestContext()
    # Hand-computed hex for EngineSpeed=1000rpm, EngineTemp=25degC (see
    # encode_frame_test.py's oracle comment for the derivation).
    result = decode_frame(
        ax, DecodeFrameInput(database=DB, message_name="EngineData", data_hex="a00f410000000000")
    )
    assert result.error.code == ""
    assert result.message_name == "EngineData"
    assert result.frame_id == 0x100
    assert abs(result.signal_values["EngineSpeed"] - 1000.0) < 1e-6
    assert abs(result.signal_values["EngineTemp"] - 25.0) < 1e-6
    assert result.signal_units["EngineSpeed"] == "rpm"
    assert result.signal_units["EngineTemp"] == "degC"


def test_decode_frame_hex_prefix_and_separators_tolerated():
    ax = AxiomTestContext()
    result = decode_frame(
        ax,
        DecodeFrameInput(
            database=DB, message_name="EngineData", data_hex="0xA0:0F:41:00:00:00:00:00"
        ),
    )
    assert result.error.code == ""
    assert abs(result.signal_values["EngineSpeed"] - 1000.0) < 1e-6


def test_decode_frame_value_table_label():
    ax = AxiomTestContext()
    result = decode_frame(ax, DecodeFrameInput(database=DB, message_name="GearStatus", data_hex="02"))
    assert result.error.code == ""
    assert result.signal_values["Gear"] == 2.0
    assert result.signal_labels["Gear"] == "Neutral"


def test_decode_frame_multiplexed_only_returns_active_group():
    ax = AxiomTestContext()
    # Selector=1 -> only Selector and ValueB should be decoded (ValueA belongs
    # to the Selector=0 group and must not appear).
    result = decode_frame(
        ax, DecodeFrameInput(database=DB, message_name="MuxedFrame", data_hex="017b000000000000")
    )
    assert result.error.code == ""
    assert "ValueB" in result.signal_values
    assert "ValueA" not in result.signal_values
    assert abs(result.signal_values["ValueB"] - 12.3) < 1e-6


def test_decode_frame_wrong_length_is_a_structured_error():
    ax = AxiomTestContext()
    result = decode_frame(ax, DecodeFrameInput(database=DB, message_name="EngineData", data_hex="aabb"))
    assert result.error.code == "OUT_OF_RANGE"


def test_decode_frame_malformed_hex_is_a_structured_error():
    ax = AxiomTestContext()
    result = decode_frame(
        ax, DecodeFrameInput(database=DB, message_name="EngineData", data_hex="not-hex-zz")
    )
    assert result.error.code == "INVALID_INPUT"


def test_decode_frame_message_not_found_is_a_structured_error():
    ax = AxiomTestContext()
    result = decode_frame(
        ax, DecodeFrameInput(database=DB, message_name="NoSuchMessage", data_hex="00")
    )
    assert result.error.code == "MESSAGE_NOT_FOUND"


def test_encode_then_decode_round_trip_matches_original_values():
    from gen.messages_pb2 import EncodeFrameInput
    from nodes.encode_frame import encode_frame

    ax = AxiomTestContext()
    encoded = encode_frame(
        ax,
        EncodeFrameInput(
            database=DB,
            message_name="EngineData",
            signal_values={"EngineSpeed": 4321.25, "EngineTemp": -12.0},
        ),
    )
    assert encoded.error.code == ""
    decoded = decode_frame(
        ax, DecodeFrameInput(database=DB, message_name="EngineData", data_hex=encoded.data_hex)
    )
    assert decoded.error.code == ""
    assert abs(decoded.signal_values["EngineSpeed"] - 4321.25) < 1e-6
    assert abs(decoded.signal_values["EngineTemp"] - (-12.0)) < 1e-6
