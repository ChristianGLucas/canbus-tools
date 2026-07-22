# canbus-tools

Composable [Axiom](https://axiom.dev) nodes for automotive CAN-bus message
encoding, decoding, and database introspection. Built for the Axiom
marketplace (`christiangeorgelucas/canbus-tools`).

Wraps [canmatrix](https://github.com/ebroecker/canmatrix) (BSD-3-Clause) — a
mature, pure-Python CAN database library — to work with DBC, KCD, SYM, and
ARXML message databases: parse them, encode/decode CAN frame payloads
against them, convert between formats, and structurally diff two revisions.

## Nodes

- **ParseDatabase** — parse a CAN database (DBC/KCD/SYM/ARXML) into its full
  structural contents: every message and every signal (bit position, byte
  order, linear scaling, min/max, unit, value tables, multiplexing).
- **EncodeFrame** — encode named physical signal values into a message's raw
  CAN frame payload bytes, identified by message name or frame ID.
- **DecodeFrame** — decode raw CAN frame payload bytes back into named,
  physically-scaled signal values (the inverse of EncodeFrame), including
  units and any enumerated value-table labels.
- **ConvertDatabase** — convert a CAN database from its source format into
  another supported format (dbc, kcd, sym).
- **CompareDatabases** — structurally diff two CAN database revisions:
  messages/signals added, removed, or changed.

All nodes are pure input-to-output, deterministic, and stateless — no
filesystem, network, or secrets, and no dependency on any live CAN bus
interface (offline database + payload processing only).

## License

MIT — see [LICENSE](./LICENSE). Wraps canmatrix (BSD-3-Clause), lxml
(BSD-3-Clause), attrs (MIT), and click (BSD-3-Clause).
