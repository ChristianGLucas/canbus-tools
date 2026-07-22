"""Shared test fixtures for christiangeorgelucas/canbus-tools.

Not a test file itself (no test_ functions) — imported by the *_test.py
files alongside it.
"""
from gen.axiom_context import SecretStatus


class AxiomTestContext:
    """Minimal AxiomContext implementation for unit tests."""

    class _Logger:
        def debug(self, msg: str, **attrs) -> None: pass
        def info(self, msg: str, **attrs) -> None: pass
        def warn(self, msg: str, **attrs) -> None: pass
        def error(self, msg: str, **attrs) -> None: pass

    class _Secrets:
        def __init__(self, m: dict, revoked: set) -> None:
            self._m = m or {}
            self._revoked = revoked or set()

        def get(self, name: str):
            v = self._m.get(name)
            return (v, True) if v is not None else ("", False)

        def status(self, name: str) -> SecretStatus:
            if name in self._m:
                return SecretStatus.AVAILABLE
            if name in self._revoked:
                return SecretStatus.REVOKED
            return SecretStatus.UNSET

    def __init__(self, secrets_map: dict | None = None, revoked_names: set | None = None) -> None:
        self.log = self._Logger()
        self.secrets = self._Secrets(secrets_map or {}, revoked_names)
        self.execution_id = "test-execution-id"
        self.flow_id = "test-flow-id"
        self.tenant_id = "test-tenant-id"


# A small, realistic DBC: two plain signals (one negative-offset signed
# signal to exercise sign handling), an enumerated (value-table) signal, and
# a simple-multiplexed message (a selector signal plus two mutually
# exclusive payload signals) — the three shapes real automotive DBCs use.
DBC_FIXTURE = '''VERSION ""

BS_:

BU_: ECU1 ECU2

BO_ 256 EngineData: 8 ECU1
 SG_ EngineSpeed : 0|16@1+ (0.25,0) [0|16383.75] "rpm" ECU2
 SG_ EngineTemp : 16|8@1- (1,-40) [-40|215] "degC" ECU2

BO_ 512 GearStatus: 1 ECU1
 SG_ Gear : 0|8@1+ (1,0) [0|3] "" ECU2

BO_ 768 MuxedFrame: 8 ECU1
 SG_ Selector M : 0|8@1+ (1,0) [0|1] "" ECU2
 SG_ ValueA m0 : 8|8@1+ (1,0) [0|255] "" ECU2
 SG_ ValueB m1 : 8|16@1+ (0.1,0) [0|6553.5] "V" ECU2

VAL_ 512 Gear 0 "Park" 1 "Reverse" 2 "Neutral" 3 "Drive" ;
'''

# Same EngineData message, but EngineSpeed's factor and max were rescaled
# and a new signal + a new message were added — used to exercise
# CompareDatabases against a real, hand-authored revision.
DBC_FIXTURE_REVISED = '''VERSION ""

BS_:

BU_: ECU1 ECU2

BO_ 256 EngineData: 8 ECU1
 SG_ EngineSpeed : 0|16@1+ (0.5,0) [0|32767.5] "rpm" ECU2
 SG_ EngineTemp : 16|8@1- (1,-40) [-40|215] "degC" ECU2
 SG_ OilPressure : 24|8@1+ (1,0) [0|255] "kPa" ECU2

BO_ 512 GearStatus: 1 ECU1
 SG_ Gear : 0|8@1+ (1,0) [0|3] "" ECU2

VAL_ 512 Gear 0 "Park" 1 "Reverse" 2 "Neutral" 3 "Drive" ;
'''

# A minimal KCD document describing one message with one signal — used to
# exercise multi-format parsing/conversion without relying on ConvertDatabase
# to have produced it first.
KCD_FIXTURE = '''<?xml version="1.0" encoding="UTF-8"?>
<NetworkDefinition xmlns="http://kayak.2codeornot2code.org/1.0">
  <Document name="fixture">canbus-tools test fixture</Document>
  <Node name="ECU1" id="1"/>
  <Bus name="CANBus">
    <Message id="0x140" name="WheelSpeed" length="2">
      <Producer><NodeRef id="1"/></Producer>
      <Signal name="Speed" offset="0" length="16">
        <Value slope="0.1" max="6553.5" unit="km/h"/>
      </Signal>
    </Message>
  </Bus>
</NetworkDefinition>
'''
