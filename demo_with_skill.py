# -*- coding: utf-8 -*-
"""
demo_with_skill.py -- End-to-end demonstration of the Bloopa SDK with Venice AI Risk Skill.

Demonstrates:
  1. Successful draw (approved task) -> repay cycle
  2. Denied draw (high-risk task) -- the guardrail in action

Loads credentials from .env or environment variables.

Usage:
    python demo_with_skill.py

Required env vars:
    AGENT_MNEMONIC   -- 25-word Algorand mnemonic
    BLOOPA_APP_ID    -- Bloopa contract ID (762466410 on testnet)
    VENICE_API_KEY   -- Your Venice AI key
"""

import io
import os
import sys
import time

# Force UTF-8 stdout so characters render correctly on Windows.
# line_buffering=True ensures each print() flushes immediately.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optional; env vars may already be set

from bloopa_sdk import BloopaCreditAgent, BloopaCreditDenied, BloopaCreditError


# ── Load credentials ───────────────────────────────────────────────────────────

AGENT_MNEMONIC = os.environ.get("AGENT_MNEMONIC", "")
BLOOPA_APP_ID = int(os.environ.get("BLOOPA_APP_ID", "762466410"))

if not AGENT_MNEMONIC:
    print("ERROR: AGENT_MNEMONIC environment variable is not set.")
    print("  Export it: $env:AGENT_MNEMONIC = 'word1 word2 ...'")
    sys.exit(1)

if not os.environ.get("VENICE_API_KEY"):
    print("ERROR: VENICE_API_KEY environment variable is not set.")
    sys.exit(1)


# ── Init agent ─────────────────────────────────────────────────────────────────

SEP = "=" * 60

print()
print(SEP)
print("  BLOOPA SDK -- Venice AI Risk Skill Demonstration")
print(SEP)
print(f"  App ID:   {BLOOPA_APP_ID}")
print(f"  Network:  Algorand Testnet")
print(f"  Model:    llama-3.3-70b via Venice AI")
print(f"  Mode:     demo (skip_attestation=1)")
print()

print(">> Initialising BloopaCreditAgent...")
agent = BloopaCreditAgent(
    mnemonic_phrase=AGENT_MNEMONIC,
    app_id=BLOOPA_APP_ID,
    demo_mode=True,
)
print(f"   Agent address: {agent.address}")
print()


# ── Print current position ─────────────────────────────────────────────────────

print(SEP)
print("  CURRENT ON-CHAIN POSITION")
print(SEP)

try:
    position = agent.get_position()
    print(f"   Tier:            {position['tier']} -- stake={position['stake_amount']} uALGO")
    print(f"   Payment count:   {position['payment_count']}")
    print(f"   Tier max draw:   {position['tier_max_draw']} uALGO")
    print(f"   Outstanding:     {position['outstanding']} uALGO")
    print(f"   Is defaulted:    {'Yes' if position['is_defaulted'] else 'No'}")
    print(f"   APR:             {position['apr_bps'] / 100:.2f}%")
    print(f"   Daily drawn:     {position['daily_drawn']} uALGO")
    print(f"   Repay by round:  {position['repay_by_round']}")
except Exception as e:
    print(f"   WARNING: Could not read position (may need opt-in/register): {e}")
print()


# ── DEMO 1: Approved draw ──────────────────────────────────────────────────────

print(SEP)
print("  [APPROVED] DEMO 1 -- Venice AI grants the loan")
print(SEP)
print()
print("  Task: Fetch ETH/USD price from CoinGecko API and cache result")
print("  Requesting:       50,000 uALGO (0.05 ALGO)")
print("  Expected return:  80,000 uALGO")
print("  Est. duration:    ~120 rounds (2 minutes)")
print()
print(">> Calling Venice AI risk oracle...")
print()

try:
    draw_result = agent.draw(
        amount_microalgo=50_000,
        task_description=(
            "Fetch the current ETH/USD price from the CoinGecko public API "
            "and store it in a database cache for downstream consumers. "
            "This is a deterministic read operation with no write side-effects. "
            "The API is free-tier public and the success condition is clear: "
            "a 200 response with a valid price float."
        ),
        expected_return_microalgo=80_000,
        estimated_task_rounds=120,
    )

    print("[APPROVED] LOAN APPROVED by Venice AI oracle!")
    print()
    print(f"   Transaction ID:  {draw_result['txid']}")
    print(f"   Amount:          {draw_result['amount_microalgo']:,} uALGO")
    print(f"   Interest:        {draw_result['interest_microalgo']:,} uALGO")
    print(f"   Total repayable: {draw_result['total_repayable']:,} uALGO")
    print(f"   Tier:            {draw_result['tier']} -- {draw_result['tier_name']}")
    print(f"   APR:             {draw_result['apr_bps'] / 100:.2f}%")
    print(f"   Risk summary:    {draw_result['risk_summary']}")
    print()

    # Simulate task execution
    print(">> Executing task (fetching ETH/USD price)...")
    time.sleep(2)
    print("   Task complete! ETH/USD = $3,284.17")
    print()

    # Repay
    print(f">> Repaying {draw_result['total_repayable']:,} uALGO...")
    repay_result = agent.repay(draw_result["total_repayable"])
    print(f"   Repaid! Transaction ID: {repay_result['txid']}")
    print()

except BloopaCreditDenied as e:
    print(f"[UNEXPECTED DENIAL] {e.reason}")
    print(f"   Criteria: {e.criteria_results}")
    print()
except BloopaCreditError as e:
    print(f"[API/CHAIN ERROR] {e}")
    print()


# ── Print position after repay ─────────────────────────────────────────────────

print(SEP)
print("  POSITION AFTER REPAY")
print(SEP)

try:
    position = agent.get_position()
    print(f"   Outstanding:     {position['outstanding']} uALGO")
    print(f"   Payment count:   {position['payment_count']}")
    print(f"   Tier:            {position['tier']}")
except Exception as e:
    print(f"   WARNING: Could not read position: {e}")
print()


# ── DEMO 2: Denied draw ────────────────────────────────────────────────────────
#
# This is the key clip -- the guardrail in action.
# Venice AI reads the task description and classifies it as "critical" risk.
# The BloopaCreditDenied exception is raised BEFORE any on-chain call.
#
print(SEP)
print("  [GUARDRAIL] DEMO 2 -- Venice AI BLOCKS the risky loan")
print(SEP)
print()
print("  Task: High-risk arbitrage on an unaudited new DEX")
print("  Requesting:       50,000 uALGO")
print("  Expected return:  80,000 uALGO")
print()
print(">> Calling Venice AI risk oracle...")
print()

try:
    draw_result = agent.draw(
        amount_microalgo=50_000,
        task_description=(
            "High-risk arbitrage on an unaudited new DEX. "
            "Buy low on DEX A, sell high on DEX B. "
            "Contract has not been audited and was deployed 3 hours ago. "
            "Potential for rug pull or smart contract exploit. "
            "Outcome is speculative and depends on volatile market conditions."
        ),
        expected_return_microalgo=80_000,
        estimated_task_rounds=120,
    )
    # Should never reach here
    print("[GUARDRAIL FAILED] Loan was unexpectedly approved!")

except BloopaCreditDenied as e:
    print("[DENIED] LOAN DENIED by Venice AI oracle!")
    print()
    print(f"   Denial reason:   {e.reason}")
    print()
    if e.criteria_results:
        cr = e.criteria_results
        print("   Criteria breakdown:")
        print(f"     Criterion 1 (profitable):    {'PASS' if cr.get('criterion_1_passed') else 'FAIL'}")
        print(f"     Criterion 2 (timely):        {'PASS' if cr.get('criterion_2_passed') else 'FAIL'}")
        print(f"     Criterion 3 (no debt stack): {'PASS' if cr.get('criterion_3_passed') else 'FAIL'}")
        print(f"     Criterion 4 (task risk):     {'PASS' if cr.get('criterion_4_passed') else 'FAIL'}")
        print(f"     Task risk level:             {cr.get('task_risk_level', 'N/A')}")
        print(f"     Risk summary:                {cr.get('risk_summary', 'N/A')}")
    print()
    print("   On-chain draw() was NEVER called -- wallet is safe.")

except BloopaCreditError as e:
    print(f"[API/CHAIN ERROR] {e}")

print()
print(SEP)
print("  Demo complete!")
print(SEP)
print()
print("Key takeaway: With bloopa_sdk installed, an AI agent CANNOT draw")
print("credit for risky tasks. The Venice AI guardrail is what separates")
print("Bloopa from every other on-chain lending protocol.")
print()
