# canbus-tools

Composable [Axiom](https://axiomide.com) nodes for automotive CAN-bus message
encoding, decoding, and database introspection. Built for the Axiom
marketplace (`christiangeorgelucas/canbus-tools`).

Wraps [canmatrix](https://github.com/ebroecker/canmatrix) (BSD-3-Clause) — a
mature, pure-Python CAN database library — to work with DBC, KCD, SYM, and
ARXML message databases: parse them, encode/decode CAN frame payloads
against them, convert between formats, and structurally diff two revisions.

## Use it from your agent or app

Every node in this package is a **live, auto-scaling API endpoint** on the
[Axiom](https://axiomide.com) marketplace — call it from an AI agent or your own
code, with nothing to self-host.

**📦 See it on the marketplace:**
https://dev.axiomide.com/marketplace/christiangeorgelucas/canbus-tools@0.1.0

**Hook it up to an AI agent (MCP).** Add Axiom's hosted MCP server to any MCP
client and every node becomes a typed tool your agent can call — search the
catalog, inspect a schema, and invoke it directly.

```bash
# Claude Code
claude mcp add --transport http axiom https://api.axiomide.com/mcp \
  --header "Authorization: Bearer $AXIOM_API_KEY"
```

Claude Desktop, Cursor, or any config-based client:

```json
{
  "mcpServers": {
    "axiom": {
      "type": "http",
      "url": "https://api.axiomide.com/mcp",
      "headers": { "Authorization": "Bearer YOUR_AXIOM_API_KEY" }
    }
  }
}
```

**Call it from the CLI.**

```bash
axiom invoke christiangeorgelucas/canbus-tools/ParseDatabase --input '{ ... }'
```

**Call it over HTTP.**

```bash
curl -X POST https://api.axiomide.com/invocations/v1/nodes/christiangeorgelucas/canbus-tools/0.1.0/ParseDatabase \
  -H "Authorization: Bearer $AXIOM_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{ ... }'
```

> Input/output schema for each node is on the marketplace page above, or via
> `axiom inspect node christiangeorgelucas/canbus-tools/ParseDatabase`.

### Get started free

Install the CLI:

```bash
# macOS / Linux — Homebrew
brew install axiomide/tap/axiom

# macOS / Linux — install script
curl -fsSL https://raw.githubusercontent.com/AxiomIDE/axiom-releases/main/install.sh | sh
```

**Windows:** download the `windows/amd64` `.zip` from the
[releases page](https://github.com/AxiomIDE/axiom-releases/releases), unzip it,
and put `axiom.exe` on your `PATH`.

Then `axiom version` to verify, `axiom login` (GitHub or Google) to authenticate,
and create an API key under **Console → API Keys**. Docs and sign-up at
**[axiomide.com](https://axiomide.com)**.

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
