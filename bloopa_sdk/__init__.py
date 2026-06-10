__version__ = "0.2.0"

"""
Bloopa SDK — LLM-gated credit for the Bloopa AI agent protocol on Algorand.

LLM provider is selected via the ORACLE_PROVIDER environment variable:
    ORACLE_PROVIDER=venice      → Venice AI, llama-3.3-70b (default)
    ORACLE_PROVIDER=anthropic   → Anthropic, claude-haiku-4-5-20251001

Core public surface::

    from bloopa_sdk import BloopaCreditAgent, BloopaCreditDenied

    agent = BloopaCreditAgent(mnemonic_phrase="...", app_id=762466410)
    try:
        result = agent.draw(
            amount_microalgo=50_000,
            task_description="Fetch ETH/USD from CoinGecko",
            expected_return_microalgo=80_000,
        )
    except BloopaCreditDenied as e:
        print(e.reason)

x402 HTTP-native payments (requires: pip install "bloopa-sdk[x402]")::

    from bloopa_sdk import BloopX402Client

    client = BloopX402Client(agent)
    response = client.get("https://x402.goplausible.xyz/examples/weather")
    print(response.text)
"""

from .oracle import RiskOracle, RiskDecision, CriteriaEvaluation
from .agent import BloopaCreditAgent, ProtocolConfig
from .exceptions import (
    BloopaCreditDenied,
    BloopaCreditError,
    BloopX402PaymentError,
    BloopX402SpendLimitExceeded,
    BloopX402SetupError,
)
from .criteria import get_tier, calculate_interest, tier_name


def __getattr__(name: str):
    """Lazy-load x402 client to avoid hard dependency on x402-avm package."""
    if name == "BloopX402Client":
        try:
            from .x402_client import BloopX402Client
            return BloopX402Client
        except ImportError as exc:
            raise ImportError(
                "BloopX402Client requires the x402 extra: "
                "pip install \"bloopa-sdk[x402]\""
            ) from exc
    raise AttributeError(f"module 'bloopa_sdk' has no attribute {name!r}")


__all__ = [
    # Core
    "BloopaCreditAgent",
    "ProtocolConfig",
    "RiskOracle",
    "RiskDecision",
    "CriteriaEvaluation",
    "BloopaCreditDenied",
    "BloopaCreditError",
    "get_tier",
    "calculate_interest",
    "tier_name",
    # x402 (lazy — requires pip install "bloopa-sdk[x402]")
    "BloopX402Client",
    "BloopX402PaymentError",
    "BloopX402SpendLimitExceeded",
    "BloopX402SetupError",
]

