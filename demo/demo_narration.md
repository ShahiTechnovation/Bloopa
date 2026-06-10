# demo/demo_narration.md — Bloopa Demo Video Script

## Setup (Before You Hit Record)

| Item | Value |
|---|---|
| Browser tab | `testnet.explorer.perawallet.app/application/762466410` |
| Terminal font size | 16px minimum |
| Screen layout | Terminal left 60% · Browser right 40% |
| Run command | `python demo/demo_with_skill.py` |
| Pre-flight check | `outstanding == 0`, `daily_drawn` has headroom |

---

## Scene 1 — Approved Draw (~55 seconds)

| Time | Terminal shows | What you say |
|---|---|---|
| 0–5s | Script starts. Prints App ID `762466410` and agent Algorand address. | *"Fresh AI agent wallet. Live on Algorand testnet."* |
| 5–15s | `get_position()` result: `tier=1`, `outstanding=0`, `payment_count=22`, `apr_bps=1600`. | *"This agent has 22 repayments on-chain. Trusted tier. 16% APR. Zero outstanding debt."* |
| 15–25s | `Calling LLM risk oracle...` then approved JSON block with all four criteria `true`. | *"The oracle checks 4 criteria — is the task profitable, does it fit the repayment window, is there existing debt, is the task low risk? All four pass."* |
| 25–35s | `draw() TX confirmed. txid=...` ALGO balance increases by 50,000 microALGO. | *"50,000 microALGO issued. Funds hit the agent wallet. No human signed anything."* |
| 35–45s | `Task executing... ETH/USD price: $2,814.22` | *"Agent uses the credit to call an external API."* |
| 45–55s | `repay() TX confirmed. outstanding=0` | *"Principal plus interest repaid. Reputation score improves."* |

---

## Scene 2 — Denied Draw (~20 seconds)

| Time | Terminal shows | What you say |
|---|---|---|
| 55–60s | `--- DEMO 2 — Denied draw ---` New task description printed. | *"Same agent. Different task."* |
| 60–70s | Risk oracle returns denial JSON: `overall_approved: false`, `task_risk_level: critical`, `denial_reason: "Criterion 4 failed..."` | *"The oracle classifies this as high risk — speculative arbitrage on an unaudited contract."* |
| 70–75s | `BloopaCreditDenied raised. No transaction submitted. Wallet balance unchanged.` | *"Draw blocked. No transaction. Wallet never touched. That is the guardrail."* |

---

## Closing (5 seconds, over title card)

> *"Bloopa — on-chain credit for AI agents. Live on Algorand testnet. App ID 762466410."*
