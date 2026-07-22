"""Shared canmatrix plumbing for every node in this package.

Every node is a thin wrapper around canmatrix (BSD-3-Clause): this module
owns the boilerplate (loading/dumping a database, resolving a message,
encoding/decoding one frame, hardening the XML parser canmatrix uses for
KCD/ARXML) so each node body stays a few lines of glue.
"""
from __future__ import annotations

import io
import math
import re
import typing

import canmatrix
import canmatrix.compare
import canmatrix.formats
import lxml.etree

# --- Input bounds -----------------------------------------------------------
# Real-world DBC/ARXML/KCD files range from a few KB to tens of MB for large
# OEM-wide ARXML exports; this bound is generous headroom while still
# stopping a caller from driving unbounded parse/compare cost.
MAX_CONTENT_CHARS = 5_000_000
# Classic CAN payload is <= 8 bytes; CAN FD extends this to <= 64 bytes.
# Nothing legitimate exceeds 64.
MAX_FRAME_BYTES = 64
# Bound on expanding a complex-multiplexer range group (SG_MUL_VAL_ m0-9999
# style declarations) into individual ids.
MAX_MULTIPLEXER_IDS = 1024

SUPPORTED_LOAD_FORMATS = ("dbc", "kcd", "sym", "arxml")
SUPPORTED_DUMP_FORMATS = ("dbc", "kcd", "sym")


class CanLibError(Exception):
    """A structured, deterministic failure — never let one of these escape
    as an unhandled exception; every node catches it and fills a CanError."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _harden_lxml_default_parser() -> None:
    """canmatrix's kcd.py/arxml.py call lxml.etree.parse(f) with no explicit
    parser, which uses lxml's *default* parser. That default resolves
    entities and is therefore XXE-vulnerable to a crafted KCD/ARXML document
    (e.g. an internal-subset SYSTEM entity reading a local file) — a
    plausible caller controls `content` entirely. canmatrix exposes no way
    to inject a parser from the outside, so we hardening the *default*
    parser lxml falls back to, once, at import time. This only affects this
    process, which exists solely to run this package's nodes.
    """
    safe_parser = lxml.etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        huge_tree=False,
        dtd_validation=False,
    )
    lxml.etree.set_default_parser(safe_parser)


_harden_lxml_default_parser()


def _frame_by_id_uncached(self, arbitration_id):
    """Replacement for canmatrix.CanMatrix.frame_by_id.

    The original caches lookups in `self._frames_dict_id_extend` — but that
    attribute is declared as a plain class-level `{}` in canmatrix
    (canmatrix/canmatrix.py, CanMatrix), not an attrs instance field, and
    the DBC/KCD/etc. loaders build `.frames` directly rather than through
    `add_frame()` (which would give an instance its own dict). The result:
    every CanMatrix instance shares ONE dict for the lifetime of the
    process, so a hit for arbitration_id 0x300 in one parsed database leaks
    into `frame_by_id(0x300)` on a *different*, later-parsed database that
    has never seen that id — returning the wrong Frame instead of None.
    canmatrix.compare.compare_db calls exactly this method to match
    messages between two databases, so in a long-lived process (this node
    handles many requests) it silently produces wrong comparison results
    for a plausible caller: two unrelated CompareDatabases calls whose
    databases happen to reuse an arbitration id. We replace it with an
    uncached, correct-by-construction equivalent — the same fallback loop
    the original already falls back to on a cache miss, just always taken.
    """
    for frame in self.frames:
        if frame.arbitration_id == arbitration_id:
            return frame
    return None


canmatrix.CanMatrix.frame_by_id = _frame_by_id_uncached


def _sniff_format(content: str) -> str:
    text = content.lstrip()
    if text.startswith("<?xml") or text.startswith("<"):
        head = content[:4000]
        return "arxml" if "AUTOSAR" in head else "kcd"
    if text.startswith("FormatVersion"):
        return "sym"
    return "dbc"


def load_database(content: str, fmt: str) -> typing.Tuple["canmatrix.CanMatrix", str]:
    """Parse database `content` (already-read text) as `fmt`, or sniff a
    format when `fmt` is empty. Returns (CanMatrix, resolved_format)."""
    if not content or not content.strip():
        raise CanLibError("INVALID_DATABASE", "database content is empty")
    if len(content) > MAX_CONTENT_CHARS:
        raise CanLibError(
            "TOO_LARGE",
            f"database content is {len(content)} chars, exceeds the {MAX_CONTENT_CHARS} bound",
        )
    resolved = (fmt or "").strip().lower() or _sniff_format(content)
    if resolved not in SUPPORTED_LOAD_FORMATS:
        raise CanLibError("UNSUPPORTED_FORMAT", f"unsupported format: {fmt!r}")
    try:
        db = canmatrix.formats.loads_flat(content, import_type=resolved)
    except CanLibError:
        raise
    except Exception as e:  # canmatrix raises a variety of parser-specific errors
        raise CanLibError(
            "INVALID_DATABASE", f"failed to parse as {resolved}: {e}"
        ) from e
    if db is None or not getattr(db, "frames", None):
        raise CanLibError(
            "INVALID_DATABASE", f"no messages could be parsed as {resolved}"
        )
    return db, resolved


def dump_database(db: "canmatrix.CanMatrix", target_format: str) -> str:
    target = (target_format or "").strip().lower()
    if target not in SUPPORTED_DUMP_FORMATS:
        raise CanLibError(
            "UNSUPPORTED_FORMAT", f"unsupported target_format: {target_format!r}"
        )
    buf = io.BytesIO()
    try:
        if target == "kcd":
            # canmatrix.formats.dump's generic dispatcher hands kcd.dump a
            # bare CanMatrix, but kcd.dump actually requires a {bus_name: db}
            # cluster mapping (it iterates `for name in cluster`) — a bare
            # CanMatrix breaks with a confusing dict-construction error. Wrap
            # it ourselves; a non-empty bus name also avoids kcd.dump falling
            # back to reading a filename off the file object, which a
            # BytesIO doesn't have.
            canmatrix.formats.dump({"CANBus": db}, buf, export_type=target)
        else:
            canmatrix.formats.dump(db, buf, export_type=target)
    except Exception as e:
        raise CanLibError("INVALID_DATABASE", f"failed to export as {target}: {e}") from e
    return buf.getvalue().decode("utf-8", errors="replace")


def _multiplexer_ids(sig) -> typing.List[int]:
    if sig.mux_val is not None:
        return [int(sig.mux_val)]
    ids: typing.List[int] = []
    for lo, hi in (sig.mux_val_grp or []):
        lo, hi = int(lo), int(hi)
        if hi - lo > MAX_MULTIPLEXER_IDS:
            hi = lo + MAX_MULTIPLEXER_IDS
        ids.extend(range(lo, hi + 1))
        if len(ids) >= MAX_MULTIPLEXER_IDS:
            break
    return ids[:MAX_MULTIPLEXER_IDS]


def signal_to_dict(sig) -> dict:
    return dict(
        name=sig.name,
        start_bit=int(sig.get_startbit()),
        length=int(sig.size),
        byte_order="little_endian" if sig.is_little_endian else "big_endian",
        is_signed=bool(sig.is_signed),
        is_float=bool(sig.is_float),
        factor=float(sig.factor),
        offset=float(sig.offset),
        min=float(sig.min) if sig.min is not None else 0.0,
        max=float(sig.max) if sig.max is not None else 0.0,
        unit=sig.unit or "",
        receivers=list(sig.receivers or []),
        comment=sig.comment or "",
        is_multiplexer=bool(sig.is_multiplexer),
        is_multiplexed=sig.mux_val is not None or bool(sig.mux_val_grp),
        multiplexer_ids=_multiplexer_ids(sig),
        value_table={int(k): str(v) for k, v in (sig.values or {}).items()},
    )


def frame_to_dict(frame) -> dict:
    return dict(
        frame_id=int(frame.arbitration_id.id),
        is_extended_id=bool(frame.arbitration_id.extended),
        name=frame.name,
        length=int(frame.size),
        senders=list(frame.transmitters or []),
        comment=frame.comment or "",
        signals=[signal_to_dict(s) for s in frame.signals],
        is_multiplexed=bool(frame.is_multiplexed),
        cycle_time_ms=int(frame.cycle_time or 0),
    )


def resolve_frame(db, message_name: str, frame_id: int):
    if message_name:
        f = db.frame_by_name(message_name)
        if f is None:
            raise CanLibError(
                "MESSAGE_NOT_FOUND", f"no message named {message_name!r}"
            )
        return f
    if frame_id is not None and frame_id >= 0:
        for f in db.frames:
            if int(f.arbitration_id.id) == frame_id:
                return f
        raise CanLibError("MESSAGE_NOT_FOUND", f"no message with frame_id {frame_id}")
    raise CanLibError("INVALID_INPUT", "either message_name or frame_id must be given")


def encode_frame(frame, signal_values: typing.Mapping[str, float], strict: bool) -> bytes:
    """canmatrix's Frame.encode() treats a *numeric* value in `data` as
    already-raw (only a `str` value is run through phys2raw, to resolve a
    value-table label) — so passing our physical/scaled signal_values
    straight through would silently encode the wrong bytes (e.g. 25.0 "degC"
    for a signal with offset -40 would encode raw 25, not the raw 65 that
    actually represents 25 degC). We convert every value ourselves via
    Signal.phys2raw before handing canmatrix a raw dict.
    """
    known = {s.name: s for s in frame.signals}
    for name in signal_values:
        if name not in known:
            raise CanLibError(
                "SIGNAL_NOT_FOUND",
                f"message {frame.name!r} has no signal named {name!r}",
            )
    raw_data: dict = {}
    for name, value in signal_values.items():
        if not math.isfinite(value):
            raise CanLibError("INVALID_INPUT", f"signal {name!r} value must be finite")
        sig = known[name]
        if strict:
            lo, hi = sig.min, sig.max
            if lo is not None and hi is not None and float(lo) < float(hi):
                if not (float(lo) <= float(value) <= float(hi)):
                    raise CanLibError(
                        "OUT_OF_RANGE",
                        f"signal {name!r} value {value} outside [{lo}, {hi}]",
                    )
        try:
            raw_data[name] = sig.phys2raw(value)
        except Exception as e:
            raise CanLibError(
                "INVALID_INPUT", f"signal {name!r} value {value} could not be encoded: {e}"
            ) from e
    try:
        raw = frame.encode(raw_data)
    except CanLibError:
        raise
    except Exception as e:
        raise CanLibError("INVALID_INPUT", f"failed to encode: {e}") from e
    return bytes(raw)


def decode_frame(frame, data: bytes) -> typing.Tuple[dict, dict, dict]:
    if len(data) != frame.size:
        raise CanLibError(
            "OUT_OF_RANGE",
            f"payload is {len(data)} bytes, message {frame.name!r} expects {frame.size}",
        )
    try:
        decoded = frame.decode(bytes(data))
    except CanLibError:
        raise
    except Exception as e:
        raise CanLibError("INVALID_INPUT", f"failed to decode: {e}") from e
    values: dict = {}
    labels: dict = {}
    units: dict = {}
    for name, dsig in decoded.items():
        if not hasattr(dsig, "phys_value"):
            # e.g. the AUTOSAR PDU-container "pdus" nesting; not modeled here.
            continue
        try:
            values[name] = float(dsig.phys_value)
        except Exception:
            continue
        units[name] = dsig.signal.unit or ""
        if dsig.signal.values:
            try:
                raw_int = int(dsig.raw_value)
            except Exception:
                raw_int = None
            if raw_int is not None and raw_int in dsig.signal.values:
                labels[name] = dsig.signal.values[raw_int]
    return values, labels, units


_HEX_CLEAN_RE = re.compile(r"[\s:_-]")


def hex_to_bytes(data_hex: str) -> bytes:
    s = (data_hex or "").strip()
    if s[:2].lower() == "0x":
        s = s[2:]
    s = _HEX_CLEAN_RE.sub("", s)
    if not s:
        raise CanLibError("INVALID_INPUT", "data_hex is empty")
    if len(s) % 2 != 0:
        raise CanLibError("INVALID_INPUT", "data_hex has an odd number of hex digits")
    if len(s) // 2 > MAX_FRAME_BYTES:
        raise CanLibError(
            "TOO_LARGE", f"payload is {len(s) // 2} bytes, exceeds the {MAX_FRAME_BYTES}-byte CAN FD bound"
        )
    try:
        return bytes.fromhex(s)
    except ValueError as e:
        raise CanLibError("INVALID_INPUT", f"data_hex is not valid hex: {e}") from e


def bytes_to_hex(data: bytes) -> str:
    return data.hex()


# --- Structural diff (CompareDatabases) -------------------------------------
# The comparison itself is canmatrix.compare.compare_db's job (it knows what
# "changed" means for every field on a Frame/Signal); this only flattens its
# CompareResult tree into this package's flat CanDatabaseDiff shape.

def compare_databases(db_a, db_b) -> typing.List[dict]:
    tree = canmatrix.compare.compare_db(db_a, db_b)
    return _walk_top(tree)


def _fmt_change(child) -> typing.Optional[str]:
    if child.changes:
        old, new = child.changes[0], child.changes[1]
        return f"{child.type}: {old} -> {new}"
    if child.result in ("added", "removed"):
        return f"{child.result} {child.type}"
    return None


def _walk_top(tree) -> typing.List[dict]:
    diffs: typing.List[dict] = []
    for child in tree.children:
        if child.type != "FRAME":
            continue  # package scope is message/signal diffs, not ECU/attribute/define/valuetable diffs
        name = getattr(child.ref, "name", "?")
        if child.result == "added":
            diffs.append(dict(kind="message_added", message_name=name, signal_name="", detail="message added"))
        elif child.result == "deleted":
            diffs.append(dict(kind="message_removed", message_name=name, signal_name="", detail="message removed"))
        elif child.result == "changed":
            diffs.extend(_walk_frame(child, name))
    return diffs


def _walk_frame(frame_result, message_name: str) -> typing.List[dict]:
    diffs: typing.List[dict] = []
    leaf_details: typing.List[str] = []
    for child in frame_result.children:
        if child.type == "SIGNAL":
            sname = getattr(child.ref, "name", "?")
            if child.result == "added":
                diffs.append(dict(kind="signal_added", message_name=message_name, signal_name=sname, detail="signal added"))
            elif child.result == "deleted":
                diffs.append(dict(kind="signal_removed", message_name=message_name, signal_name=sname, detail="signal removed"))
            elif child.result == "changed":
                sub = [d for d in (_fmt_change(gc) for gc in child.children) if d]
                diffs.append(
                    dict(
                        kind="signal_changed",
                        message_name=message_name,
                        signal_name=sname,
                        detail="; ".join(sub) if sub else "changed",
                    )
                )
        else:
            d = _fmt_change(child)
            if d:
                leaf_details.append(d)
    if leaf_details:
        diffs.append(
            dict(kind="message_changed", message_name=message_name, signal_name="", detail="; ".join(leaf_details))
        )
    return diffs
