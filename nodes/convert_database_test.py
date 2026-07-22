from gen.messages_pb2 import CanDatabase, ConvertDatabaseInput
from nodes.convert_database import convert_database
from nodes.parse_database import parse_database
from gen.messages_pb2 import ParseDatabaseInput
from nodes.testkit import DBC_FIXTURE, KCD_FIXTURE, AxiomTestContext


def test_convert_database_dbc_to_sym():
    ax = AxiomTestContext()
    result = convert_database(
        ax, ConvertDatabaseInput(database=CanDatabase(content=DBC_FIXTURE, format="dbc"), target_format="sym")
    )
    assert result.error.code == ""
    assert result.database.format == "sym"
    assert "FormatVersion" in result.database.content
    assert "EngineData" in result.database.content

    # Round-trip: the converted SYM text should parse back to the same
    # messages/signals ParseDatabase reports for the original DBC.
    reparsed = parse_database(ax, ParseDatabaseInput(database=result.database))
    assert reparsed.error.code == ""
    names = {m.name for m in reparsed.messages}
    assert names == {"EngineData", "GearStatus", "MuxedFrame"}
    engine = next(m for m in reparsed.messages if m.name == "EngineData")
    speed = next(s for s in engine.signals if s.name == "EngineSpeed")
    assert abs(speed.factor - 0.25) < 1e-9
    assert speed.unit == "rpm"


def test_convert_database_dbc_to_kcd_round_trips():
    ax = AxiomTestContext()
    result = convert_database(
        ax, ConvertDatabaseInput(database=CanDatabase(content=DBC_FIXTURE, format="dbc"), target_format="kcd")
    )
    assert result.error.code == ""
    assert result.database.format == "kcd"
    assert "<NetworkDefinition" in result.database.content

    reparsed = parse_database(ax, ParseDatabaseInput(database=result.database))
    assert reparsed.error.code == ""
    names = {m.name for m in reparsed.messages}
    assert "EngineData" in names


def test_convert_database_kcd_to_dbc():
    ax = AxiomTestContext()
    result = convert_database(
        ax, ConvertDatabaseInput(database=CanDatabase(content=KCD_FIXTURE, format="kcd"), target_format="dbc")
    )
    assert result.error.code == ""
    assert result.database.format == "dbc"
    assert "BO_" in result.database.content
    assert "WheelSpeed" in result.database.content


def test_convert_database_unsupported_target_is_a_structured_error():
    ax = AxiomTestContext()
    result = convert_database(
        ax,
        ConvertDatabaseInput(
            database=CanDatabase(content=DBC_FIXTURE, format="dbc"), target_format="not-a-real-format"
        ),
    )
    assert result.error.code == "UNSUPPORTED_FORMAT"


def test_convert_database_invalid_source_is_a_structured_error():
    ax = AxiomTestContext()
    result = convert_database(
        ax, ConvertDatabaseInput(database=CanDatabase(content="garbage", format="dbc"), target_format="kcd")
    )
    assert result.error.code == "INVALID_DATABASE"
