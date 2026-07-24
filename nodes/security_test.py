"""Security-focused tests for the KCD/ARXML XML parsing path and input
bounds. Not a node-specific test file — imported nowhere, just discovered by
pytest like the other *_test.py files.
"""
from gen.messages_pb2 import CanDatabase, ParseDatabaseInput
from nodes._can_lib import MAX_FRAME_BYTES, hex_to_bytes, CanLibError
from nodes.parse_database import parse_database
from nodes.testkit import AxiomTestContext

# canmatrix's kcd.py/arxml.py call lxml.etree.parse(f) with no explicit
# parser (using whatever lxml's *default* parser is) — lxml's out-of-the-box
# default resolves entities, so a crafted document with an internal-subset
# SYSTEM entity can read an arbitrary local file and splice its contents into
# the parsed tree (classic XXE). canmatrix exposes no parser-injection hook,
# so _can_lib hardens lxml's *process-wide default parser* at import time
# (resolve_entities=False, no_network=True, load_dtd=False). This proves
# that hardening actually takes effect through the whole ParseDatabase path,
# not just when calling lxml directly.
_XXE_KCD = """<?xml version="1.0"?>
<!DOCTYPE NetworkDefinition [
  <!ENTITY xxe SYSTEM "file:///etc/hostname">
]>
<NetworkDefinition xmlns="http://kayak.2codeornot2code.org/1.0">
  <Document name="&xxe;">test</Document>
  <Bus name="B1">
    <Message id="0x100" name="M1" length="1"/>
  </Bus>
</NetworkDefinition>
"""


def test_kcd_external_entity_is_not_resolved():
    ax = AxiomTestContext()
    result = parse_database(ax, ParseDatabaseInput(database=CanDatabase(content=_XXE_KCD, format="kcd")))
    # Either outcome is acceptable from a security standpoint (fail closed),
    # but the entity must never be resolved into the response, and the node
    # must never crash — it returns a structured error. In practice the
    # hardened parser rejects the external-entity declaration outright
    # (INVALID_DATABASE), which is what we assert; the two checks below are
    # a belt-and-suspenders guard against a future canmatrix/lxml upgrade
    # silently reverting to entity resolution, on the (extremely unlikely)
    # chance parsing then "succeeds" anyway.
    assert result.error.code == "INVALID_DATABASE"
    serialized = str(result)
    assert "&xxe;" not in serialized
    try:
        hostname = open("/etc/hostname").read().strip()
    except OSError:
        hostname = ""
    if hostname:  # only a meaningful check where the target file actually exists
        assert hostname not in serialized


def test_oversized_hex_payload_is_rejected():
    try:
        hex_to_bytes("aa" * (MAX_FRAME_BYTES + 1))
        assert False, "expected CanLibError"
    except CanLibError as e:
        assert e.code == "TOO_LARGE"
