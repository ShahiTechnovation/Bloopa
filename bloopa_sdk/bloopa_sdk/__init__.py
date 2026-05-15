__version__ = "0.1.0"

"""
Bloopa SDK — LLM-gated credit for the Bloopa AI agent protocol on Algorand.

LLM provider is selected via the ORACLE_PROVIDER environment variable:
    ORACLE_PROVIDER=venice      → Venice AI, llama-3.3-70b (default)
    ORACLE_PROVIDER=anthropic   → Anthropic, claude-haiku-4-5-20251001

Public surface:

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
"""

from .oracle import RiskOracle, RiskDecision, CriteriaEvaluation
from .agent import BloopaCreditAgent
from .exceptions import BloopaCreditDenied, BloopaCreditError
from .criteria import get_tier, calculate_interest, tier_name

__all__ = [
    "BloopaCreditAgent",
    "RiskOracle",
    "RiskDecision",
    "CriteriaEvaluation",
    "BloopaCreditDenied",
    "BloopaCreditError",
    "get_tier",
    "calculate_interest",
    "tier_name",
]
