from gen.axiom_context import AxiomContext
from gen.messages_pb2 import (
    CanDatabaseDiff,
    CanError,
    CompareDatabasesInput,
    CompareDatabasesOutput,
)

from nodes._can_lib import CanLibError, compare_databases as _compare_databases, load_database


def compare_databases(ax: AxiomContext, input: CompareDatabasesInput) -> CompareDatabasesOutput:
    """Structurally diff two CAN database revisions and report every message
    and signal added, removed, or changed (e.g. a moved start bit, a
    rescaled factor/offset, a widened range, a renamed receiver) — useful
    for reviewing what an updated DBC actually changes before it ships to a
    fleet. database_a and database_b may be different source formats.
    """
    try:
        db_a, _fmt_a = load_database(input.database_a.content, input.database_a.format)
        db_b, _fmt_b = load_database(input.database_b.content, input.database_b.format)
        raw_diffs = _compare_databases(db_a, db_b)
        diffs = [CanDatabaseDiff(**d) for d in raw_diffs]
        return CompareDatabasesOutput(diffs=diffs)
    except CanLibError as e:
        return CompareDatabasesOutput(error=CanError(code=e.code, message=e.message))
    except Exception as e:  # pragma: no cover - defensive backstop, never crash
        return CompareDatabasesOutput(error=CanError(code="INTERNAL", message=str(e)))
