from gen.axiom_context import AxiomContext
from gen.messages_pb2 import CanError, EncodeFrameInput, EncodeFrameOutput

from nodes._can_lib import CanLibError, bytes_to_hex, encode_frame as _encode_frame
from nodes._can_lib import load_database, resolve_frame


def encode_frame(ax: AxiomContext, input: EncodeFrameInput) -> EncodeFrameOutput:
    """Encode one CAN message's named physical signal values into the raw
    payload bytes a device would put on the bus, per the message's
    definition in the given database. Identify the message by name or by
    frame_id (leave the other at its default: "" / -1). In strict mode, a
    signal value outside its declared [min, max] range fails with
    OUT_OF_RANGE instead of being encoded silently; an unknown signal name
    always fails with SIGNAL_NOT_FOUND rather than being silently ignored.
    """
    try:
        db, _fmt = load_database(input.database.content, input.database.format)
        frame = resolve_frame(db, input.message_name, input.frame_id)
        raw = _encode_frame(frame, dict(input.signal_values), input.strict)
        return EncodeFrameOutput(
            data_hex=bytes_to_hex(raw),
            frame_id=int(frame.arbitration_id.id),
            message_name=frame.name,
            dlc=len(raw),
        )
    except CanLibError as e:
        return EncodeFrameOutput(error=CanError(code=e.code, message=e.message))
    except Exception as e:  # pragma: no cover - defensive backstop, never crash
        return EncodeFrameOutput(error=CanError(code="INTERNAL", message=str(e)))
