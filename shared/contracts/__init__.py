"""Inter-service contracts — request/response schemas shared by services.

These are the wire formats that flow between services and to the
WhatsApp workspace. Versioned with a ``v1`` namespace so future
revisions can coexist.
"""

from .whatsapp_contract import (
    WhatsAppMessage,
    WhatsAppDeliveryRequest,
    WhatsAppDeliveryResponse,
    WhatsappChannel,
)
from .automation_contract import (
    OrderCheckRequest,
    OrderCheckResult,
    DelayCheckRequest,
    DelayCheckResult,
    CompensationDecision,
    StockCheckRequest,
    StockCheckResult,
    DisputeTriageRequest,
    DisputeTriageResult,
)
from .ai_contract import (
    AIJudgmentRequest,
    AIJudgmentResult,
    AIClassifyRequest,
    AIClassifyResult,
    AIExtractRequest,
    AIExtractResult,
    AISummarizeRequest,
    AISummarizeResult,
)

__all__ = [
    "WhatsAppMessage",
    "WhatsAppDeliveryRequest",
    "WhatsAppDeliveryResponse",
    "WhatsappChannel",
    "OrderCheckRequest",
    "OrderCheckResult",
    "DelayCheckRequest",
    "DelayCheckResult",
    "CompensationDecision",
    "StockCheckRequest",
    "StockCheckResult",
    "DisputeTriageRequest",
    "DisputeTriageResult",
    "AIJudgmentRequest",
    "AIJudgmentResult",
    "AIClassifyRequest",
    "AIClassifyResult",
    "AIExtractRequest",
    "AIExtractResult",
    "AISummarizeRequest",
    "AISummarizeResult",
]
