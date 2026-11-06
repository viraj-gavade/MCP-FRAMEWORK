"""Test-only MCP boundary evidence helpers.

These helpers observe the existing call boundary; they do not alter configured
allowlists or turn denied requests into permitted calls.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class InvocationEvidence:
    tool_requested: Optional[str] = None
    invocation_attempted: bool = False
    server_receipt: bool = False
    receipt_id: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def record_invocation(tool_name: str, receipt_id: Optional[str] = None) -> InvocationEvidence:
    """Record an invocation only at an instrumented server receipt."""
    return InvocationEvidence(
        tool_requested=tool_name,
        invocation_attempted=True,
        server_receipt=True,
        receipt_id=receipt_id,
    )
