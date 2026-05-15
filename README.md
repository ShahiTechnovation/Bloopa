# Bloopa — On-chain Credit for AI Agents

> **The first protocol where an LLM decides if an AI agent's loan is responsible before it's issued.**

**Live on Algorand Testnet · App ID: 762466410**  
[View on Explorer](https://testnet.explorer.perawallet.app/application/762466410) · [bloopa.xyz](https://bloopa.xyz)

---

## What Is Bloopa?

AI agents can execute code, call APIs, and transact on-chain autonomously — but they cannot borrow money. There is no credit bureau for software bots. Today, if an agent runs out of funds mid-task, it stops. It cannot take out a microloan, complete its work, and repay automatically.

Bloopa is an on-chain credit bureau for autonomous AI agents on Algorand. Agents stake ALGO to register an identity, record their transaction history on-chain to build reputation, and draw undercollateralised credit lines — up to 10× their original stake — based on that history. The credit limit, tier, and interest rate are all computed deterministically by the smart contract with no off-chain intervention.

What makes Bloopa different is the risk oracle. Before any draw reaches the chain, an LLM evaluates four hardcoded criteria against the agent's stated task. If the task is speculative, the agent already has outstanding debt, the expected return doesn't cover the loan cost, or the task won't finish before the repayment deadline — the draw is denied and no transaction is ever submitted. The LLM is the guardrail, not the human.

---

## Live Demo Output

### ✅ Approved draw — ETH price fetch

```
========================================
 BLOOPA CREDIT AGENT — LIVE DEMO
========================================
App ID:         762466410
Agent address:  7XQ3...DEMO

[on-chain] Querying position...
  stake_amount:    1_000_000 microALGO
  payment_count:   22
  credit_limit:    12_000_000 microALGO
  outstanding:     0 microALGO
  tier:            1 (Trusted)  |  APR: 16.00%

Calling LLM risk oracle...
  ✅ Criterion 1: return (80,000) > cost (50,001) — PASS
  ✅ Criterion 2: task rounds (120) < 86,400 — PASS
  ✅ Criterion 3: outstanding == 0 — PASS
  ✅ Criterion 4: risk level = low — PASS
  Oracle: APPROVED
  Risk summary: Low-risk deterministic API call with clear profit margin.

[on-chain] draw() submitted...
  txid:             TXID_ABCDEF123456
  amount drawn:     50,000 microALGO
  interest:         1 microALGO
  total repayable:  50,001 microALGO

Task executing...
  ETH/USD price: $2,814.22 ✓

[on-chain] repay() submitted...
  txid:             TXID_REPAY789012
  outstanding:      0 microALGO
========================================
  DEMO COMPLETE ✅
========================================
```

### 🚫 Denied draw — high-risk arbitrage

```
--- DEMO 2 — Denied draw ---
Task: Speculative arbitrage on unaudited new DEX contracts

Calling LLM risk oracle...
  ✅ Criterion 1: return covers cost — PASS
  ✅ Criterion 2: task fits window — PASS
  ✅ Criterion 3: no outstanding debt — PASS
  ❌ Criterion 4: risk level = critical — FAIL

  Oracle: DENIED
  Reason: Criterion 4 failed: task risk level is 'critical' —
          speculative arbitrage on an unaudited contract is never permitted.

BloopaCreditDenied raised. No transaction submitted.
Wallet balance: unchanged.
```

---

## Architecture

### 3-Layer Stack

| Layer | Technology | Description |
|---|---|---|
| **Smart Contract** | Algorand Python · ARC-4 · Puya | On-chain credit bureau, slashing, state management |
| **Python SDK** | `bloopa_sdk` · Venice AI / Anthropic | LLM-gated draw, four-criteria risk oracle |
| **Frontend** | React · Vite · Pera/Defly Wallets | Agent terminal, position dashboard, live chain data |

### Oracle Criteria (immutable — cannot be overridden by agent code)

1. **Return must exceed cost**: `expected_return > loan + interest`
2. **Task fits repayment window**: `estimated_rounds < 86,400` (~24 hours)
3. **No outstanding debt**: `outstanding == 0` (no loan stacking, ever)
4. **Task risk is acceptable**: LLM assigns `low` or `medium` risk. `high` and `critical` are always denied.

### Tier System

| Tier | Name | Min Payments | Max Draw | APR |
|---|---|---|---|---|
| 0 | Fresh | 0 | 0.10 ALGO | 24% |
| 1 | Trusted | 10 | 0.50 ALGO | 16% |
| 2 | Veteran | 50 | 2.00 ALGO | 9% |
| 3 | Elite | 100 | 5.00 ALGO | 4% |

---

## Quick Start

```bash
# Clone
git clone https://github.com/ShahiTechnovation/Bloopa
cd Bloopa

# Install SDK
pip install -e "./bloopa_sdk"

# Set environment variables
cp contracts/.env.example contracts/.env
# Fill in: AGENT_MNEMONIC, BLOOPA_APP_ID=762466410, VENICE_API_KEY

# Run demo
python demo_with_skill.py

# Run tests
python test_sdk.py
```

---

## SDK Usage

```python
import os
from bloopa_sdk import BloopaCreditAgent, BloopaCreditDenied

agent = BloopaCreditAgent(
    mnemonic_phrase=os.environ["AGENT_MNEMONIC"],
    app_id=762466410,
)

# Oracle runs internally — Venice AI or Anthropic evaluates 4 criteria
try:
    result = agent.draw(
        amount_microalgo=50_000,
        task_description="Fetch ETH/USD price from CoinGecko",
        expected_return_microalgo=80_000,
        estimated_task_rounds=120,
    )
    # {"txid": "...", "amount_microalgo": 50000, "interest_microalgo": 1,
    #  "tier": 1, "tier_name": "Trusted", "risk_summary": "..."}

    agent.repay(result["total_repayable"])

except BloopaCreditDenied as e:
    print(f"Denied: {e.reason}")
    # No on-chain transaction was submitted
```

---

## Oracle Providers

The LLM provider is controlled by the `ORACLE_PROVIDER` environment variable.

### Venice AI (default)

```bash
export ORACLE_PROVIDER=venice
export VENICE_API_KEY=your-venice-key
python demo_with_skill.py
```

Model: `llama-3.3-70b`. No extra install required (`openai` package already included).

### Anthropic

```bash
export ORACLE_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
pip install -e "./bloopa_sdk[anthropic]"
python demo_with_skill.py
```

Model: `claude-haiku-4-5-20251001`. Uses `client.beta.messages.parse()` for structured output.

---

## Contract Reference

**Deployed:** Algorand Testnet · App ID: `762466410`  
[View on Pera Explorer →](https://testnet.explorer.perawallet.app/application/762466410)

### ABI Methods

| Method | Signature | Description |
|---|---|---|
| `opt_in` | bare (OptIn) | Bootstrap local state for new agent wallet |
| `register` | `register(pay)→void` | Stake ALGO, initialise agent identity |
| `record_payment` | `record_payment(uint64)→uint64` | Record off-chain M2M payment, boost credit limit |
| `draw` | `draw(uint64,byte[32])→void` | Draw credit; attestation hash verified on mainnet |
| `repay` | `repay(pay)→void` | Repay outstanding balance |
| `slash` | `slash(address)→void` | Anyone can slash a delinquent agent after 30 rounds |
| `get_position` | `get_position(address)→(uint64×5)` | Read agent's full position (readonly) |
| `enable_attestation` | `enable_attestation()→void` | Turn on on-chain hash verification (mainnet) |
| `fund` | bare (NoOp) | Fund the contract treasury |

### State Schema

| Scope | Key | Type | Description |
|---|---|---|---|
| Global | `treasury_balance` | uint64 | Total ALGO held by contract |
| Global | `total_agents` | uint64 | Number of registered agents |
| Local | `stake_amount` | uint64 | Agent's staked ALGO |
| Local | `payment_count` | uint64 | Number of recorded repayments |
| Local | `total_repaid` | uint64 | Lifetime repayment total |
| Local | `outstanding` | uint64 | Current unpaid balance |
| Local | `credit_limit` | uint64 | Current computed credit limit |
| Local | `is_defaulted` | uint64 | 1 if agent has been slashed |
| Local | `last_payment_round` | uint64 | Last round a payment was made |

---

## V2 Roadmap

- **USDC/ASA denomination** — Real dollar-denominated microloans for production use
- **ZK proof attestation** — Decentralise the oracle with verifiable computation
- **Base L2 + Solana deployment** — Reach the broader AI agent ecosystem
- **Bilateral payment verification** — Prevent fake history inflation, require counterparty signatures
- **Treasury insurance pool** — Absorb defaults automatically without manual top-ups
- **Agent identity registry** — Persistent credit history across wallet rekeys

---

## Known Limitations

> [!NOTE]
> Bloopa is a testnet prototype built at AlgoBharat Hack Series 3.0. These are honest limitations, not bugs.

- **Slash window is 30 rounds (~30 seconds)** — Intentionally short for demo purposes. Production should use `DAY_IN_ROUNDS` (86,400 rounds ≈ 24 hours).
- **`payment_count` is self-reported** — Any agent can call `record_payment()` without a real counterparty. V2 requires bilateral signing from both parties.
- **`skip_attestation=1` on testnet** — The `draw()` contract does not verify the attestation hash in demo mode. Call `enable_attestation()` before mainnet deployment.
- **Treasury funded manually** — The contract must be seeded with ALGO before any draw can succeed. V2 will implement automated liquidity management.

---

## License

MIT License.  
Built at **AlgoBharat Hack Series 3.0** on Algorand.
