# Bloopa SDK — Claude Skill (Risk Oracle)

## What this is

Bloopa is a credit protocol for AI agents on Algorand. Instead of requiring over-collateralisation, agents stake a small amount of ALGO, build repayment history, and unlock progressively larger credit lines across four tiers. The system works without any human in the loop — an AI agent can request a microloan, complete a task, and repay automatically.

This SDK is the **Claude Skill** that sits between an AI agent and the Bloopa smart contract. Before any funds are released, the SDK calls the Anthropic API to run a structured 4-criteria risk assessment. If the task is too risky, the return doesn't cover the cost, the agent already has outstanding debt, or the task can't be completed within 24 hours — the draw is denied before the transaction is ever submitted. This keeps the protocol solvent and makes Bloopa safe to operate without human oversight.

---

## Install

```bash
pip install -r requirements.txt
```

> **Anthropic SDK version check required:**
> `client.messages.parse()` with structured output requires `anthropic>=0.40.0`.
> Run `pip show anthropic` before use. If below 0.40, upgrade:
> ```bash
> pip install --upgrade anthropic
> ```

---

## Environment variables required

```bash
ANTHROPIC_API_KEY=sk-ant-...
AGENT_MNEMONIC="word word word ... (25 words)"
BLOOPA_APP_ID=12345678
```

Create a `.env` file or export these in your shell.

---

## Usage — one line

```python
import os
from bloopa_sdk import BloopaCreditAgent

agent = BloopaCreditAgent(
    mnemonic_phrase=os.environ["AGENT_MNEMONIC"],
    app_id=int(os.environ["BLOOPA_APP_ID"]),
)

# One call — Claude Skill runs internally, draw submitted if approved
result = agent.draw(
    amount_microalgo=50_000,
    task_description="Fetching the current ETH/USD price from CoinGecko public API",
    expected_return_microalgo=80_000,
    estimated_task_rounds=120,
)
print(result)
# {
#   "txid": "ABC123...",
#   "amount_microalgo": 50000,
#   "interest_microalgo": 3,
#   "total_repayable": 50003,
#   "tier": 0,
#   "apr_bps": 2400,
#   "risk_summary": "Low-risk deterministic API call with positive expected return."
# }

# After task completes, repay
agent.repay(result["total_repayable"])
```

---

## Usage — manual (for custom agents)

Use `RiskOracle` directly if you want to evaluate risk before deciding whether to submit the transaction yourself:

```python
from algosdk.v2client import algod
from bloopa_sdk import RiskOracle, BloopaCreditDenied

algod_client = algod.AlgodClient("", "https://testnet-api.algonode.cloud")
oracle = RiskOracle(algod_client=algod_client)

try:
    decision = oracle.evaluate(
        agent_address="YOUR_ALGORAND_ADDRESS",
        amount_microalgo=50_000,
        payment_count=5,             # from get_position()
        outstanding_microalgo=0,     # from get_position()
        task_description="Fetch ETH price from CoinGecko",
        expected_return_microalgo=80_000,
        estimated_task_rounds=120,
    )
    print("Approved! Tier:", decision.tier)
    print("Interest:", decision.interest_microalgo, "microALGO")
    print("Attestation hash:", decision.attestation_hash.hex())
    # Pass decision.attestation_hash to your draw() ATC call

except BloopaCreditDenied as e:
    print("Denied:", e.reason)
    print("Criteria breakdown:", e.criteria_results)
```

---

## How the risk oracle works

When you call `agent.draw()`, the SDK:

1. Reads the agent's current on-chain position (tier, outstanding debt).
2. Computes the interest charge using the same formula as the smart contract.
3. Sends the task description and financial parameters to Claude.
4. Claude evaluates 4 criteria and returns a structured JSON decision.
5. If all 4 criteria pass, the SDK computes the attestation hash and submits the draw transaction.
6. If any criterion fails, a `BloopaCreditDenied` exception is raised — no transaction is ever submitted.

---

## The 4 criteria Claude evaluates

1. **Return covers cost** — The agent's expected return from the task must be strictly greater than the draw amount plus the interest charge. If the task isn't profitable, it's not worth the credit risk.

2. **Task fits repayment window** — The task must be completable within 86,400 rounds (approximately 24 hours on Algorand). The smart contract enforces a 24-hour repayment deadline; tasks that cannot complete in time will always default.

3. **No outstanding debt** — The agent must have zero outstanding debt before taking a new loan. Loan stacking — borrowing against existing unpaid debt — is not permitted and will be denied immediately.

4. **Task risk level is low or medium** — Claude assesses the described task and assigns a risk level: *low* (deterministic API calls, calculations), *medium* (external dependencies with clear success criteria), *high* (speculation or unclear outcomes), or *critical* (irreversible financial actions). Only low and medium tasks are approved.

---

## Tier system

Your tier is determined by how many repayments you have on record. Higher tiers unlock larger draws and lower interest rates.

| Tier | Name    | Min Repayments | Max Draw     | Daily Cap    | APR  |
|------|---------|----------------|--------------|--------------|------|
| 0    | Fresh   | 0              | 0.10 ALGO    | 0.50 ALGO    | 24%  |
| 1    | Trusted | 10             | 0.50 ALGO    | 2.00 ALGO    | 16%  |
| 2    | Veteran | 50             | 2.00 ALGO    | 10.00 ALGO   | 9%   |
| 3    | Elite   | 100            | 5.00 ALGO    | 25.00 ALGO   | 4%   |

*(All amounts in microALGO × 10^-6 = ALGO equivalents shown)*

---

## V2 roadmap note

The current attestation mechanism uses `sha256(sender + amount + round)` as a testnet placeholder. In V2, the Claude Skill will sign the hash with an ed25519 key registered as `protocol_signer` on-chain, and the contract will verify the signature via `op.ed25519verify_bare`. The `enable_attestation()` contract method switches the contract from demo mode to production mode. No SDK changes are required to support this upgrade.
