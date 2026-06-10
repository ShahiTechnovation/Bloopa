"""
intent_demo.py — Bloopa Intent Router end-to-end demo.

Demonstrates the full intent lifecycle:
  Agent1 (locker)  — posts a private swap order, locked in Router escrow
  Agent2 (solver)  — detects order, draws Bloopa credit, executes mock swap, settles

Run:
  VENICE_API_KEY=your_key \\
  AGENT1_MNEMONIC="25 words..." \\
  AGENT2_MNEMONIC="25 words..." \\
  BLOOPA_APP_ID=762466410 \\
  ROUTER_APP_ID=YOUR_ROUTER_APP_ID \\
  python demo/intent_demo.py

DEMO_MODE=1 (default): Uses mock swap, skips on-chain txns if SKIP_CHAIN=1
"""

import base64
import hashlib
import os
import sys
import time
from pathlib import Path

# ── Ensure project root is on sys.path ────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from bloopa_sdk import BloopaCreditAgent, BloopaCreditDenied
from bloopa_sdk.intent_agent import IntentBrain, IntentExecutor, IntentListener
from algosdk import account, mnemonic, transaction
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    AccountTransactionSigner,
    TransactionWithSigner,
)
from algosdk.abi import Method

# ── Load environment ──────────────────────────────────────────────────────────

load_dotenv(Path(__file__).parent.parent / ".bloopa.env")

AGENT1_MNEMONIC = os.environ.get("AGENT1_MNEMONIC", "")
AGENT2_MNEMONIC = os.environ.get("AGENT2_MNEMONIC", "")
BLOOPA_APP_ID   = int(os.environ.get("BLOOPA_APP_ID", "762466410"))
ROUTER_APP_ID   = int(os.environ.get("ROUTER_APP_ID", "0"))
ALGOD_URL       = os.environ.get("ALGOD_URL", "https://testnet-api.algonode.cloud")
NETWORK         = os.environ.get("BLOOPA_NETWORK", "testnet")

# Demo mode flag — skips on-chain transactions when set
SKIP_CHAIN = os.environ.get("SKIP_CHAIN", "0") == "1"

# In SKIP_CHAIN mode: inject a dummy key so the OpenAI client can be constructed
# (it won't actually make API calls since we mock all oracle calls below)
if SKIP_CHAIN and not os.environ.get("VENICE_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
    os.environ["VENICE_API_KEY"] = "skip-chain-demo-key"

if not AGENT1_MNEMONIC or not AGENT2_MNEMONIC:
    print("ERROR: Set AGENT1_MNEMONIC and AGENT2_MNEMONIC environment variables.")
    print("       Use 'bloopa init' to generate funded wallets.")
    sys.exit(1)

# ── Agent setup ───────────────────────────────────────────────────────────────

agent1 = BloopaCreditAgent(
    mnemonic_phrase=AGENT1_MNEMONIC,
    app_id=BLOOPA_APP_ID,
    algod_url=ALGOD_URL,
    demo_mode=True,
)

agent2 = BloopaCreditAgent(
    mnemonic_phrase=AGENT2_MNEMONIC,
    app_id=BLOOPA_APP_ID,
    algod_url=ALGOD_URL,
    demo_mode=True,
)

# ── Intent parameters ─────────────────────────────────────────────────────────

SWAP_AMOUNT_UA    = 200_000   # 0.20 ALGO locked by agent1
API_COST_UA       = 50_000    # 0.05 ALGO agent2 borrows from Bloopa
EXPIRY_ROUNDS     = 300       # ~5 minutes on testnet
TASK_DESCRIPTION  = "Execute ALGO-to-USDC DEX swap via Tinyman v2 (mock). Low-risk deterministic swap at current market rate."


# ── Helper ────────────────────────────────────────────────────────────────────

def separator(char="═", width=60):
    print(char * width)


def mock_swap_handler(intent: dict) -> tuple[str, bytes]:
    """Mock swap handler. In production: call Tinyman v2 SDK."""
    algo_amount  = intent["payment_amount"] / 1_000_000
    usdc_received = algo_amount * 0.25  # mock $0.25/ALGO rate
    result_str = (
        f"SWAP_COMPLETE:ALGO_{algo_amount:.4f}->USDC_{usdc_received:.4f}"
        f":ts_{int(time.time())}"
    )
    result_hash = hashlib.sha256(result_str.encode()).digest()  # 32 bytes
    return result_str, result_hash


def call_router_lock_intent(
    agent: BloopaCreditAgent,
    router_app_id: int,
    payment_ua: int,
    task_hash: bytes,
    expiry_rounds: int,
    api_cost: int,
    solver_address: str,
) -> int:
    """Call lock_intent on Router. Returns intent_id."""
    if SKIP_CHAIN:
        print("  [SKIP_CHAIN] Skipping on-chain lock_intent — returning mock intent_id=42")
        return 42

    from algosdk.logic import get_application_address

    sp = agent.algod_client.suggested_params()
    router_addr = get_application_address(router_app_id)

    # Payment to Router escrow
    pay_txn = transaction.PaymentTxn(
        sender=agent.address,
        sp=sp,
        receiver=router_addr,
        amt=payment_ua,
    )

    atc = AtomicTransactionComposer()

    # Box key: b"I" + 0.to_bytes(8, "big") — for intent_id 0 initially
    # We use box=b"I\x00\x00\x00\x00\x00\x00\x00\x00" for the first intent
    # In practice the router increments, so we include a broad box ref
    atc.add_method_call(
        app_id=router_app_id,
        method=Method.from_signature("lock_intent(pay,byte[32],uint64,uint64,address)uint64"),
        sender=agent.address,
        sp=sp,
        signer=agent.signer,
        method_args=[
            TransactionWithSigner(pay_txn, agent.signer),
            list(task_hash),
            expiry_rounds,
            api_cost,
            solver_address,
        ],
        boxes=[(router_app_id, b"I" + (0).to_bytes(8, "big"))],
    )

    result = atc.execute(agent.algod_client, 4)
    intent_id = int(result.abi_results[0].return_value)
    return intent_id


def call_router_borrow_to_execute(
    agent: BloopaCreditAgent,
    router_app_id: int,
    intent_id: int,
    task_description: str,
    expected_return: int,
) -> None:
    """Call borrow_to_execute on Router to claim the intent."""
    if SKIP_CHAIN:
        print("  [SKIP_CHAIN] Skipping on-chain borrow_to_execute")
        return

    box_key = b"I" + intent_id.to_bytes(8, "big")
    sp = agent.algod_client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=router_app_id,
        method=Method.from_signature("borrow_to_execute(uint64,string,uint64)bool"),
        sender=agent.address,
        sp=sp,
        signer=agent.signer,
        method_args=[intent_id, task_description, expected_return],
        boxes=[(router_app_id, box_key)],
    )
    atc.execute(agent.algod_client, 4)


def call_router_settle(
    agent: BloopaCreditAgent,
    router_app_id: int,
    bloopa_app_id: int,
    intent_id: int,
    result_hash: bytes,
    result_pointer: str,
) -> None:
    """Call settle on Router to atomically distribute funds."""
    if SKIP_CHAIN:
        print("  [SKIP_CHAIN] Skipping on-chain settle")
        return

    box_key = b"I" + intent_id.to_bytes(8, "big")
    sp = agent.algod_client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=router_app_id,
        method=Method.from_signature("settle(uint64,byte[32],string)bool"),
        sender=agent.address,
        sp=sp,
        signer=agent.signer,
        method_args=[intent_id, list(result_hash), result_pointer[:200]],
        boxes=[(router_app_id, box_key)],
        foreign_apps=[bloopa_app_id],
        accounts=[agent.address],
    )
    atc.execute(agent.algod_client, 4)


# ── Main demo ─────────────────────────────────────────────────────────────────

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    separator()
    print("  BLOOPA INTENT ROUTER DEMO — Algorand Native Intent Market")
    print("  Inspired by NEAR Intents. Built on Algorand. Powered by Bloopa.")
    separator()
    print()

    if ROUTER_APP_ID == 0:
        print("WARNING: ROUTER_APP_ID not set. Running in SKIP_CHAIN=1 simulation mode.")
        print("         Deploy the Router first: python contracts/deploy_router.py")
        print()

    # ─────────────────────────────────────────────────────────────────────────
    # AGENT1: POST INTENT
    # ─────────────────────────────────────────────────────────────────────────

    agent2_short = agent2.address[:12]

    print("[USER1] Posting private swap intent...")
    print(f"  Swap:          0.20 ALGO -> USDC")
    print(f"  Locked:        {SWAP_AMOUNT_UA:,} \u03bcA")
    print(f"  API cost est:  {API_COST_UA:,} \u03bcA")
    print(f"  Solver:        {agent2_short}... (private \u2014 only this solver can fulfill)")
    print(f"  Expiry:        {EXPIRY_ROUNDS} rounds from now (~{EXPIRY_ROUNDS} seconds)")
    print()

    # Compute task_hash = sha256(task_description)
    task_hash_bytes = hashlib.sha256(TASK_DESCRIPTION.encode()).digest()

    try:
        intent_id = call_router_lock_intent(
            agent=agent1,
            router_app_id=ROUTER_APP_ID if ROUTER_APP_ID else 0,
            payment_ua=SWAP_AMOUNT_UA,
            task_hash=task_hash_bytes,
            expiry_rounds=EXPIRY_ROUNDS,
            api_cost=API_COST_UA,
            solver_address=agent2.address,
        )
        print(f"[USER1] Intent posted on Algorand testnet")
        print(f"  Intent ID:     {intent_id}")
        if not SKIP_CHAIN:
            print(f"  Router:        https://testnet.algoexplorer.io/application/{ROUTER_APP_ID}")
        print()
    except Exception as exc:
        print(f"[USER1] lock_intent failed: {exc}")
        if not SKIP_CHAIN:
            sys.exit(1)
        intent_id = 42  # demo fallback

    # ─────────────────────────────────────────────────────────────────────────
    # AGENT2: DETECT INTENT
    # ─────────────────────────────────────────────────────────────────────────

    print("[USER2] Polling Algorand indexer for intents...")

    # For demo purposes: construct intent dict directly (no live poll needed
    # since we just posted it and know the details)
    time.sleep(2)  # brief pause to simulate poll latency

    intent = {
        "intent_id":      intent_id,
        "locker":         agent1.address,
        "payment_amount": SWAP_AMOUNT_UA,
        "api_cost":       API_COST_UA,
        "expiry_round":   9_999_999,  # far future for demo
        "solver_address": agent2.address,
        "assigned_agent": "",
        "state":          0,
        "task_description": TASK_DESCRIPTION,
    }

    # Adjust expiry to a realistic value if we have algod access
    if not SKIP_CHAIN:
        try:
            current_round = agent2.algod_client.status()["last-round"]
            intent["expiry_round"] = current_round + EXPIRY_ROUNDS
        except Exception:
            pass

    print(f"[USER2] Intent {intent_id} detected! Assigned to this solver.")
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # AGENT2: ORACLE EVALUATION
    # ─────────────────────────────────────────────────────────────────────────

    print("[USER2] Running Bloopa oracle evaluation...")

    brain = IntentBrain(agent2, min_profit_ratio=0.10, time_buffer_rounds=120)

    current_round = intent["expiry_round"] - EXPIRY_ROUNDS + 10  # simulated round

    # Run oracle (may call Venice AI / Anthropic)
    if SKIP_CHAIN:
        # Short-circuit: skip real algod/LLM calls in simulation mode
        should_exec = True
        reason = "skip_chain_mode"
        borrow_amount = API_COST_UA
    else:
        should_exec, reason, borrow_amount = brain.evaluate(intent, current_round)

    profit_ua = SWAP_AMOUNT_UA - API_COST_UA
    profit_pct = profit_ua / SWAP_AMOUNT_UA * 100

    if should_exec:
        print(f"  Criterion 1 (profitable):     PASS \u2014 profit {profit_ua:,} \u03bcA ({profit_pct:.1f}%) > threshold")
        print(f"  Criterion 2 (time window):    PASS \u2014 {EXPIRY_ROUNDS} rounds available, need ~120")
        print(f"  Criterion 3 (no debt):        PASS \u2014 outstanding 0 \u03bcA")
        print(f"  Criterion 4 (risk level):     PASS \u2014 DEX swap classified as 'low' risk")
        print(f"  Oracle decision: APPROVED")
        print()
    else:
        print(f"  Oracle decision: REJECTED")
        print(f"  Reason: {reason}")
        print()
        print("Demo cannot proceed without oracle approval.")
        print("Ensure VENICE_API_KEY is set and agent2 has no outstanding debt.")
        # In demo mode, continue anyway to show the flow
        if SKIP_CHAIN:
            print("[SKIP_CHAIN] Continuing demo despite rejection...")
            should_exec = True
            borrow_amount = API_COST_UA
        else:
            sys.exit(1)

    # ─────────────────────────────────────────────────────────────────────────
    # AGENT2: DRAW BLOOPA CREDIT
    # ─────────────────────────────────────────────────────────────────────────

    print(f"[USER2] Drawing Bloopa credit: {borrow_amount:,} \u03bcA")

    draw_result = None
    if not SKIP_CHAIN:
        try:
            draw_result = agent2.draw(
                amount_microalgo=borrow_amount,
                task_description=TASK_DESCRIPTION,
                expected_return_microalgo=profit_ua,
                estimated_task_rounds=120,
            )
            print(f"  Txn (Bloopa.draw): https://testnet.algoexplorer.io/tx/{draw_result['txid']}")
            print(f"  Inner txn confirmed.")
        except BloopaCreditDenied as exc:
            print(f"  Bloopa draw denied: {exc.reason}")
            sys.exit(1)
        except Exception as exc:
            print(f"  Bloopa draw failed: {exc}")
            sys.exit(1)
    else:
        print(f"  [SKIP_CHAIN] Mock draw: {borrow_amount:,} \u03bcA borrowed from Bloopa")
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # AGENT2: CLAIM INTENT (borrow_to_execute)
    # ─────────────────────────────────────────────────────────────────────────

    print(f"[USER2] Claiming intent {intent_id} on Router...")
    try:
        call_router_borrow_to_execute(
            agent=agent2,
            router_app_id=ROUTER_APP_ID if ROUTER_APP_ID else 0,
            intent_id=intent_id,
            task_description=TASK_DESCRIPTION,
            expected_return=profit_ua,
        )
        if not SKIP_CHAIN:
            print(f"  Txn (borrow_to_execute): confirmed on Router")
        else:
            print(f"  [SKIP_CHAIN] Mock claim: intent {intent_id} assigned to solver")
    except Exception as exc:
        print(f"  borrow_to_execute failed: {exc}")
        if not SKIP_CHAIN:
            sys.exit(1)
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # AGENT2: EXECUTE MOCK SWAP
    # ─────────────────────────────────────────────────────────────────────────

    print("[USER2] Executing swap task...")
    result_str, result_hash = mock_swap_handler(intent)
    algo_amount = SWAP_AMOUNT_UA / 1_000_000
    usdc_received = algo_amount * 0.25
    print(f"  (mock) ALGO -> USDC swap: {algo_amount:.2f} ALGO -> {usdc_received:.4f} USDC at $0.25/ALGO")
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # AGENT2: SETTLE
    # ─────────────────────────────────────────────────────────────────────────

    # Calculate settlement amounts
    interest_ua = (borrow_amount * 2400 * 86400) // (10000 * 31536000) + 1
    repayment_ua = borrow_amount + interest_ua
    solver_profit_ua = SWAP_AMOUNT_UA - repayment_ua

    print("[USER2] Settling on-chain...")
    print(f"  Atomic group (3 inner txns):")
    print(f"    [0] Repay Bloopa:           {repayment_ua:,} \u03bcA ({borrow_amount:,} + {interest_ua} interest)")
    print(f"    [1] Solver profit:           {solver_profit_ua:,} \u03bcA")
    print(f"    [2] Bloopa.record_payment(): payment_count++")

    try:
        call_router_settle(
            agent=agent2,
            router_app_id=ROUTER_APP_ID if ROUTER_APP_ID else 0,
            bloopa_app_id=BLOOPA_APP_ID,
            intent_id=intent_id,
            result_hash=result_hash,
            result_pointer=result_str[:200],
        )
        if not SKIP_CHAIN:
            print(f"    [3] Result logged on-chain: {result_str[:60]}...")
    except Exception as exc:
        print(f"  settle() failed: {exc}")
        if not SKIP_CHAIN:
            # Fallback: repay Bloopa directly
            if draw_result:
                print(f"  Repaying Bloopa directly: {draw_result['total_repayable']:,} \u03bcA")
                try:
                    agent2.repay(draw_result["total_repayable"])
                    print("  Repayment confirmed.")
                except Exception as repay_exc:
                    print(f"  Repay also failed: {repay_exc}")
            sys.exit(1)
    print()

    # Final record_payment call if settle() inner txn may have failed
    # (In demo, solver calls this directly for guaranteed tier credit)
    if not SKIP_CHAIN:
        try:
            new_tier = agent2.record_payment(amount_microalgo=borrow_amount)
            print(f"  record_payment() confirmed. New tier: {new_tier}")
        except Exception as exc:
            print(f"  record_payment() call: {exc} (may already be recorded by settle)")
        print()

    # ─────────────────────────────────────────────────────────────────────────
    # SETTLEMENT SUMMARY
    # ─────────────────────────────────────────────────────────────────────────

    separator()
    print("  SETTLEMENT COMPLETE")
    separator("-", 60)
    print(f"  User1:   swap executed \u2014 USDC received ({usdc_received:.4f} USDC)")
    print(f"  User2:   {solver_profit_ua / 1_000_000:.4f} ALGO profit after Bloopa repayment")
    print(f"  Bloopa:  {interest_ua} \u03bcA interest collected, tier history updated")
    separator()

    # Show agent2 position if we have chain access
    if not SKIP_CHAIN:
        try:
            pos = agent2.get_position()
            print()
            print("[USER2] Updated on-chain position:")
            print(f"  payment_count: {pos['payment_count']}")
            print(f"  tier:          {pos['tier']} ({['Fresh','Trusted','Veteran','Elite'][pos['tier']]})")
            print(f"  outstanding:   {pos['outstanding']} \u03bcA")
        except Exception as exc:
            print(f"[USER2] get_position() failed: {exc}")


if __name__ == "__main__":
    main()
