from gen.axiom_context import AxiomContext
from gen.messages_pb2 import CanDatabase, CanError, ConvertDatabaseInput, ConvertDatabaseOutput

from nodes._can_lib import CanLibError, dump_database, load_database


def convert_database(ax: AxiomContext, input: ConvertDatabaseInput) -> ConvertDatabaseOutput:
    """Convert a CAN database from its source format into another supported
    format (dbc, kcd, or sym), re-serializing every message and signal it
    contains. Useful for migrating a database authored in one tool's native
    format to one another tool expects.
    """
    try:
        db, _fmt = load_database(input.database.content, input.database.format)
        converted_text = dump_database(db, input.target_format)
        target = input.target_format.strip().lower()
        return ConvertDatabaseOutput(database=CanDatabase(content=converted_text, format=target))
    except CanLibError as e:
        return ConvertDatabaseOutput(error=CanError(code=e.code, message=e.message))
    except Exception as e:  # pragma: no cover - defensive backstop, never crash
        return ConvertDatabaseOutput(error=CanError(code="INTERNAL", message=str(e)))
