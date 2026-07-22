from gen.messages_pb2 import CanDatabase, ParseDatabaseInput
from nodes.parse_database import parse_database
from nodes.testkit import DBC_FIXTURE, KCD_FIXTURE, AxiomTestContext


def test_parse_database_dbc():
    ax = AxiomTestContext()
    result = parse_database(ax, ParseDatabaseInput(database=CanDatabase(content=DBC_FIXTURE, format="dbc")))
    assert result.error.code == ""
    assert result.format == "dbc"
    names = {m.name for m in result.messages}
    assert names == {"EngineData", "GearStatus", "MuxedFrame"}

    engine = next(m for m in result.messages if m.name == "EngineData")
    assert engine.frame_id == 0x100
    assert engine.length == 8
    assert engine.senders == ["ECU1"]
    sig_by_name = {s.name: s for s in engine.signals}
    speed = sig_by_name["EngineSpeed"]
    assert speed.start_bit == 0
    assert speed.length == 16
    assert speed.byte_order == "little_endian"
    assert speed.is_signed is False
    assert abs(speed.factor - 0.25) < 1e-9
    assert abs(speed.max - 16383.75) < 1e-6
    assert speed.unit == "rpm"
    assert speed.receivers == ["ECU2"]

    temp = sig_by_name["EngineTemp"]
    assert temp.is_signed is True
    assert abs(temp.offset - (-40)) < 1e-9
    assert abs(temp.min - (-40)) < 1e-6

    gear = next(m for m in result.messages if m.name == "GearStatus")
    gear_sig = gear.signals[0]
    assert gear_sig.value_table == {0: "Park", 1: "Reverse", 2: "Neutral", 3: "Drive"}

    mux = next(m for m in result.messages if m.name == "MuxedFrame")
    assert mux.is_multiplexed is True
    mux_sig_by_name = {s.name: s for s in mux.signals}
    assert mux_sig_by_name["Selector"].is_multiplexer is True
    assert mux_sig_by_name["ValueA"].is_multiplexed is True
    assert list(mux_sig_by_name["ValueA"].multiplexer_ids) == [0]
    assert list(mux_sig_by_name["ValueB"].multiplexer_ids) == [1]


def test_parse_database_kcd():
    ax = AxiomTestContext()
    result = parse_database(ax, ParseDatabaseInput(database=CanDatabase(content=KCD_FIXTURE, format="kcd")))
    assert result.error.code == ""
    assert result.format == "kcd"
    assert [m.name for m in result.messages] == ["WheelSpeed"]
    sig = result.messages[0].signals[0]
    assert sig.name == "Speed"
    assert sig.unit == "km/h"


def test_parse_database_format_autodetect():
    ax = AxiomTestContext()
    # format left empty: DBC content should be sniffed correctly.
    result = parse_database(ax, ParseDatabaseInput(database=CanDatabase(content=DBC_FIXTURE, format="")))
    assert result.error.code == ""
    assert result.format == "dbc"


def test_parse_database_empty_content_is_a_structured_error():
    ax = AxiomTestContext()
    result = parse_database(ax, ParseDatabaseInput(database=CanDatabase(content="", format="dbc")))
    assert result.error.code == "INVALID_DATABASE"
    assert len(result.messages) == 0


def test_parse_database_garbage_content_is_a_structured_error():
    ax = AxiomTestContext()
    result = parse_database(
        ax, ParseDatabaseInput(database=CanDatabase(content="not a can database at all !!", format="dbc"))
    )
    assert result.error.code == "INVALID_DATABASE"


def test_parse_database_unsupported_format_is_a_structured_error():
    ax = AxiomTestContext()
    result = parse_database(
        ax, ParseDatabaseInput(database=CanDatabase(content=DBC_FIXTURE, format="not-a-real-format"))
    )
    assert result.error.code == "UNSUPPORTED_FORMAT"
