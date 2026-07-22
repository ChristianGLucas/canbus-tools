from gen.messages_pb2 import CanDatabase, EncodeFrameInput
from nodes.encode_frame import encode_frame
from nodes.testkit import DBC_FIXTURE, AxiomTestContext

DB = CanDatabase(content=DBC_FIXTURE, format="dbc")


def test_encode_frame_by_name():
    ax = AxiomTestContext()
    result = encode_frame(
        ax,
        EncodeFrameInput(
            database=DB,
            message_name="EngineData",
            frame_id=-1,
            signal_values={"EngineSpeed": 1000.0, "EngineTemp": 25.0},
        ),
    )
    assert result.error.code == ""
    # Hand-computed: EngineSpeed raw = 1000/0.25 = 4000 = 0x0FA0, little-endian
    # -> bytes[0:2] = a0 0f. EngineTemp raw = 25 - (-40) = 65 = 0x41 -> byte[2].
    assert result.data_hex == "a00f410000000000"
    assert result.dlc == 8
    assert result.frame_id == 0x100
    assert result.message_name == "EngineData"


def test_encode_frame_by_frame_id():
    ax = AxiomTestContext()
    result = encode_frame(
        ax,
        EncodeFrameInput(database=DB, message_name="", frame_id=0x100, signal_values={"EngineSpeed": 0.0}),
    )
    assert result.error.code == ""
    assert result.message_name == "EngineData"


def test_encode_frame_value_table_signal():
    ax = AxiomTestContext()
    result = encode_frame(
        ax,
        EncodeFrameInput(database=DB, message_name="GearStatus", frame_id=-1, signal_values={"Gear": 2.0}),
    )
    assert result.error.code == ""
    assert result.data_hex == "02"


def test_encode_frame_multiplexed_signal():
    ax = AxiomTestContext()
    result = encode_frame(
        ax,
        EncodeFrameInput(
            database=DB,
            message_name="MuxedFrame",
            frame_id=-1,
            signal_values={"Selector": 1.0, "ValueB": 12.3},
        ),
    )
    assert result.error.code == ""
    # ValueB raw = 12.3 / 0.1 = 123 = 0x7B, little-endian 16-bit at byte 1.
    assert result.data_hex == "017b000000000000"


def test_encode_frame_strict_out_of_range_is_a_structured_error():
    ax = AxiomTestContext()
    result = encode_frame(
        ax,
        EncodeFrameInput(
            database=DB,
            message_name="EngineData",
            frame_id=-1,
            signal_values={"EngineTemp": 9999.0},
            strict=True,
        ),
    )
    assert result.error.code == "OUT_OF_RANGE"
    assert result.data_hex == ""


def test_encode_frame_unknown_signal_name_is_a_structured_error_not_silently_ignored():
    # A plausible caller typo: canmatrix's own Frame.encode() silently drops
    # unrecognized keys, which would otherwise look like success while
    # quietly not encoding the value the caller asked for.
    ax = AxiomTestContext()
    result = encode_frame(
        ax,
        EncodeFrameInput(
            database=DB, message_name="EngineData", frame_id=-1, signal_values={"EngineSpeeed": 100.0}
        ),
    )
    assert result.error.code == "SIGNAL_NOT_FOUND"


def test_encode_frame_message_not_found_is_a_structured_error():
    ax = AxiomTestContext()
    result = encode_frame(
        ax, EncodeFrameInput(database=DB, message_name="NoSuchMessage", frame_id=-1, signal_values={})
    )
    assert result.error.code == "MESSAGE_NOT_FOUND"


def test_encode_frame_no_identifier_given_is_a_structured_error():
    ax = AxiomTestContext()
    result = encode_frame(ax, EncodeFrameInput(database=DB, message_name="", frame_id=-1, signal_values={}))
    assert result.error.code == "INVALID_INPUT"


def test_encode_frame_non_finite_value_is_rejected():
    ax = AxiomTestContext()
    result = encode_frame(
        ax,
        EncodeFrameInput(
            database=DB,
            message_name="EngineData",
            frame_id=-1,
            signal_values={"EngineSpeed": float("nan")},
        ),
    )
    assert result.error.code == "INVALID_INPUT"
