# Bloopa SDK

**LLM-gated micro-credit for AI agents on Algorand.**

[![PyPI version](https://img.shields.io/pypi/v/bloopa-sdk.svg)](https://pypi.org/project/bloopa-sdk/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What Is Bloopa?

Bloopa is an on-chain AI agent credit protocol built on Algorand. It lets AI agents borrow microALGO to perform tasks — but **only after a risk oracle evaluates the request and approves it**.

The oracle applies four immutable criteria before any on-chain transaction is ever submitted. If the agent's task is too risky, too expensive, already indebted, or takes too long — the draw is denied and nothing hits the chain. No exceptions.

---

## Install

```bash
pip install bloopa-sdk

# With Anthropic oracle support:
pip install bloopa-sdk[anthropic]
```

---

## Quick Start

```python
import os
from dotenv import load_dotenv
from bloopa_sdk import BloopaCreditAgent, BloopaCreditDenied

load_dotenv()

agent = BloopaCreditAgent(
    mnemonic_phrase=os.environ["AGENT_MNEMONIC"],
    app_id=int(os.environ["BLOOPA_APP_ID"]),   # 762466410 on testnet
)

try:
    result = agent.draw(
        amount_microalgo=50_000,
        task_description="Fetch the current ETH/USD price from CoinGecko and store it",
        expected_return_microalgo=80_000,
        estimated_task_rounds=120,
    )
    print(f"✅ Approved! txid={result['txid']}")
    print(f"   Repay {result['total_repayable']} microALGO when done.")

    # … run your task here …

    repay_result = agent.repay(result["total_repayable"])
    print(f"✅ Repaid: txid={repay_result['txid']}")

except BloopaCreditDenied as e:
    print(f"❌ Denied: {e.reason}")
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `AGENT_MNEMONIC` | **Yes** | 25-word Algorand mnemonic for the agent wallet |
| `BLOOPA_APP_ID` | **Yes** | `762466410` (Algorand Testnet) |
| `VENICE_API_KEY` | Default oracle | From [api.venice.ai](https://api.venice.ai) |
| `ORACLE_PROVIDER` | No | `venice` (default) or `anthropic` |
| `ANTHROPIC_API_KEY` | If `ORACLE_PROVIDER=anthropic` | Anthropic API key |

Create a `.env` file in your project root:

```env
AGENT_MNEMONIC=word1 word2 word3 ... word25
BLOOPA_APP_ID=762466410
VENICE_API_KEY=your-venice-key
ORACLE_PROVIDER=venice
```

---

## The 4 Oracle Criteria

Every `draw()` passes through the risk oracle before any transaction is submitted. All four must pass:

| # | Criterion | Condition |
|---|---|---|
| 1 | **Profitable** | `expected_return > principal + interest` |
| 2 | **Time-bounded** | `estimated_task_rounds < 86,400` (~24 h) |
| 3 | **Debt-free** | `outstanding_balance == 0` |
| 4 | **Low/medium risk** | Task description evaluates to `low` or `medium` risk |

Risk levels for criterion 4:
- `low` — deterministic, bounded (API calls, data fetches, calculations)
- `medium` — external dependencies with clear, verifiable success criteria
- `high` — speculative or unverifiable outcomes (**denied**)
- `critical` — financial speculation, unaudited contracts, irreversible actions (**denied**)

---

## Tier System

Payment history builds reputation and unlocks better terms:

| Tier | Name | Payments | Max Draw | Daily Cap | APR |
|---|---|---|---|---|---|
| 0 | Fresh | 0+ | 0.1 ALGO | 0.5 ALGO | 24% |
| 1 | Trusted | 10+ | 0.5 ALGO | 2 ALGO | 16% |
| 2 | Veteran | 50+ | 2 ALGO | 10 ALGO | 9% |
| 3 | Elite | 100+ | 5 ALGO | 25 ALGO | 4% |

---

## Full API Reference

### `BloopaCreditAgent`

```python
agent = BloopaCreditAgent(
    mnemonic_phrase: str,          # 25-word Algorand mnemonic
    app_id: int,                   # Bloopa contract app ID
    algod_url: str = "https://testnet-api.algonode.cloud",
    demo_mode: bool = True,        # False for production attestation
)
```

#### `agent.draw(...)` → `dict`

```python
result = agent.draw(
    amount_microalgo: int,         # How much to borrow
    task_description: str,         # Plain-English task (oracle reads this)
    expected_return_microalgo: int,# Must exceed principal + interest
    estimated_task_rounds: int = 300,  # Must be < 86,400
)
# Returns:
# {
#   "txid": str,
#   "amount_microalgo": int,
#   "interest_microalgo": int,
#   "total_repayable": int,
#   "tier": int,
#   "tier_name": str,
#   "apr_bps": int,
#   "risk_summary": str,
# }
```

#### `agent.repay(amount_microalgo)` → `dict`

```python
result = agent.repay(result["total_repayable"])
# Returns: {"txid": str, "repaid_microalgo": int}
```

#### `agent.get_position()` → `dict`

```python
pos = agent.get_position()
# Returns:
# {
#   "stake_amount": int,
#   "payment_count": int,
#   "tier_max_draw": int,
#   "outstanding": int,
#   "is_defaulted": int,
#   "tier": int,
#   "apr_bps": int,
#   "daily_drawn": int,
#   "repay_by_round": int,
# }
```

#### `agent.record_payment(amount_microalgo=1000)` → `int`

Records an off-chain payment to increment payment count and upgrade tier.

---

### `RiskOracle` (advanced)

Use directly if you want to separate oracle evaluation from the draw:

```python
from bloopa_sdk import RiskOracle, RiskDecision, BloopaCreditDenied
from algosdk.v2client.algod import AlgodClient

oracle = RiskOracle(algod_client=AlgodClient("", "https://testnet-api.algonode.cloud"))

try:
    decision: RiskDecision = oracle.evaluate(
        agent_address="ALGO...",
        amount_microalgo=50_000,
        payment_count=21,
        outstanding_microalgo=0,
        task_description="Fetch ETH/USD from CoinGecko",
        expected_return_microalgo=80_000,
        estimated_task_rounds=120,
    )
    print(decision.attestation_hash.hex())   # 32-byte hash for draw()
except BloopaCreditDenied as e:
    print(e.reason)
```

### Switching to the Anthropic Oracle

```bash
export ORACLE_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
pip install bloopa-sdk[anthropic]
```

Model: `claude-haiku-4-5-20251001`. The returned `RiskDecision` is identical regardless of provider.

---

### Exceptions

```python
from bloopa_sdk import BloopaCreditDenied, BloopaCreditError

try:
    result = agent.draw(...)
except BloopaCreditDenied as e:
    # Oracle denied the request (4 criteria). No tx was submitted.
    print(e.reason)           # "Criterion 4 failed: task risk level is 'critical'..."
    print(e.criteria_results) # Full dict from CriteriaEvaluation.model_dump()
except BloopaCreditError as e:
    # API or chain failure (algod unreachable, bad API key, etc.)
    print(str(e))
```

---

## Demo Mode vs Production

By default `demo_mode=True`: the attestation hash sent to the contract is `bytes(32)` (32 zero bytes), and the testnet contract skips on-chain verification. This is safe for testnet.

For production deployments where the contract verifies the attestation hash:

```python
agent = BloopaCreditAgent(
    mnemonic_phrase=...,
    app_id=...,
    demo_mode=False,   # Real SHA-256 hash computed and verified on-chain
)
```

---

## Links

- 🌐 [bloopa.xyz](https://bloopa.xyz)
- 📦 [PyPI](https://pypi.org/project/bloopa-sdk/)
- 🐙 [GitHub](https://github.com/ShahiTechnovation/Bloopa)
- 🐛 [Issues](https://github.com/ShahiTechnovation/Bloopa/issues)

---

## License

MIT — see [LICENSE](https://github.com/ShahiTechnovation/Bloopa/blob/main/LICENSE) for details.
