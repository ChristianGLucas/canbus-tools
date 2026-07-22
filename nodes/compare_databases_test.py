from gen.messages_pb2 import CanDatabase, CompareDatabasesInput
from nodes.compare_databases import compare_databases
from nodes.testkit import DBC_FIXTURE, DBC_FIXTURE_REVISED, AxiomTestContext


def test_compare_databases_identical_has_no_diffs():
    ax = AxiomTestContext()
    db = CanDatabase(content=DBC_FIXTURE, format="dbc")
    result = compare_databases(ax, CompareDatabasesInput(database_a=db, database_b=db))
    assert result.error.code == ""
    assert list(result.diffs) == []


def test_compare_databases_reports_added_removed_and_changed():
    ax = AxiomTestContext()
    result = compare_databases(
        ax,
        CompareDatabasesInput(
            database_a=CanDatabase(content=DBC_FIXTURE, format="dbc"),
            database_b=CanDatabase(content=DBC_FIXTURE_REVISED, format="dbc"),
        ),
    )
    assert result.error.code == ""
    diffs = list(result.diffs)
    kinds = {(d.kind, d.message_name, d.signal_name) for d in diffs}

    # MuxedFrame only exists in database_a (the revision drops it).
    assert ("message_removed", "MuxedFrame", "") in kinds
    # EngineData.EngineSpeed's factor and max were rescaled -> signal_changed.
    assert ("signal_changed", "EngineData", "EngineSpeed") in kinds
    speed_diff = next(d for d in diffs if d.kind == "signal_changed" and d.signal_name == "EngineSpeed")
    assert "factor" in speed_diff.detail
    # A new OilPressure signal was added to EngineData.
    assert ("signal_added", "EngineData", "OilPressure") in kinds
    # GearStatus is untouched -> no diff entries reference it.
    assert not any(d.message_name == "GearStatus" for d in diffs)


def test_compare_databases_invalid_input_is_a_structured_error():
    ax = AxiomTestContext()
    result = compare_databases(
        ax,
        CompareDatabasesInput(
            database_a=CanDatabase(content="garbage", format="dbc"),
            database_b=CanDatabase(content=DBC_FIXTURE, format="dbc"),
        ),
    )
    assert result.error.code == "INVALID_DATABASE"
