from gen.axiom_context import AxiomContext
from gen.messages_pb2 import CanError, ParseDatabaseInput, ParseDatabaseOutput

from nodes._can_lib import CanLibError, frame_to_dict, load_database


def parse_database(ax: AxiomContext, input: ParseDatabaseInput) -> ParseDatabaseOutput:
    """Parse a CAN database (DBC, KCD, SYM, or ARXML text) into its full
    structural contents: every message (arbitration ID, name, DLC, senders,
    cycle time) and every signal within it (start bit, bit length, byte
    order, signed/float, linear factor/offset, min/max, unit, receivers,
    multiplexing, and any enumerated value table). Leave format empty to
    auto-detect it from the content.
    """
    try:
        db, resolved_format = load_database(input.database.content, input.database.format)
        messages = [frame_to_dict(f) for f in db.frames]
        return ParseDatabaseOutput(format=resolved_format, messages=messages)
    except CanLibError as e:
        return ParseDatabaseOutput(error=CanError(code=e.code, message=e.message))
    except Exception as e:  # pragma: no cover - defensive backstop, never crash
        return ParseDatabaseOutput(error=CanError(code="INTERNAL", message=str(e)))
