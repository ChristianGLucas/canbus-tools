from gen.axiom_context import AxiomContext
from gen.messages_pb2 import CanError, DecodeFrameInput, DecodeFrameOutput

from nodes._can_lib import (
    CanLibError,
    decode_frame as _decode_frame,
    hex_to_bytes,
    load_database,
    resolve_frame,
)


def decode_frame(ax: AxiomContext, input: DecodeFrameInput) -> DecodeFrameOutput:
    """Decode a raw CAN frame's payload bytes into named, physically-scaled
    signal values (value = raw * factor + offset), per the message
    definition in the given database — the inverse of EncodeFrame. Also
    returns each signal's declared unit and, where the database defines an
    enumerated value table, the human-readable label for the decoded raw
    value. data_hex may be plain hex, optionally "0x"-prefixed, with
    whitespace/":"/"-" separators tolerated.
    """
    try:
        db, _fmt = load_database(input.database.content, input.database.format)
        frame = resolve_frame(db, input.message_name, input.frame_id)
        raw = hex_to_bytes(input.data_hex)
        values, labels, units = _decode_frame(frame, raw)
        return DecodeFrameOutput(
            message_name=frame.name,
            frame_id=int(frame.arbitration_id.id),
            signal_values=values,
            signal_labels=labels,
            signal_units=units,
        )
    except CanLibError as e:
        return DecodeFrameOutput(error=CanError(code=e.code, message=e.message))
    except Exception as e:  # pragma: no cover - defensive backstop, never crash
        return DecodeFrameOutput(error=CanError(code="INTERNAL", message=str(e)))
