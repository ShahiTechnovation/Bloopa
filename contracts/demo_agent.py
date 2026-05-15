"""
demo_agent.py — Bloopa testnet demo script.

Walks a full agent lifecycle:
  opt_in -> register -> record_payment x3 -> get_position
  -> draw -> repay -> get_position

Environment variables required:
  AGENT_MNEMONIC  — 25-word mnemonic of the agent account (must be funded on testnet)
  APP_ID          — Bloopa application ID (integer)

Usage:
  pip install py-algorand-sdk
  export AGENT_MNEMONIC="word1 word2 ... word25"
  export APP_ID=123456789
  python demo_agent.py
"""

import os
import time

from algosdk import account, mnemonic
from algosdk.v2client import algod
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    AccountTransactionSigner,
    TransactionWithSigner,
)
from algosdk.transaction import (
    PaymentTxn,
    StateSchema,
    ApplicationOptInTxn,
)
from algosdk import abi as sdk_abi

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

ALGOD_URL   = "https://testnet-api.algonode.cloud"
ALGOD_TOKEN = ""  # algonode public endpoint, no token needed

# Increase default timeout for slow testnet nodes
import urllib.request
_orig_urlopen = urllib.request.urlopen
def _urlopen_with_timeout(req, *args, **kwargs):
    kwargs.setdefault("timeout", 30)
    return _orig_urlopen(req, *args, **kwargs)
urllib.request.urlopen = _urlopen_with_timeout

MNEMONIC = os.environ.get("AGENT_MNEMONIC", "")
APP_ID   = int(os.environ.get("APP_ID", "0"))

if not MNEMONIC:
    raise SystemExit("ERROR: Set AGENT_MNEMONIC env variable")
if not APP_ID:
    raise SystemExit("ERROR: Set APP_ID env variable")

PRIVATE_KEY = mnemonic.to_private_key(MNEMONIC)
AGENT_ADDR  = account.address_from_private_key(PRIVATE_KEY)
SIGNER      = AccountTransactionSigner(PRIVATE_KEY)

STAKE_AMOUNT  = 1_000_000   # 1 ALGO
DRAW_AMOUNT   = 50_000      # 0.05 ALGO (well within Tier 0 cap of 100_000)

TIER_NAMES = {0: "Fresh", 1: "Trusted", 2: "Veteran", 3: "Elite"}

# Dummy 32-byte attestation hash (zeros) — skip_attestation defaults to 1
# so the contract ignores this value in demo mode.
DUMMY_ATTESTATION = [0] * 32


# ─────────────────────────────────────────────────────────────
# Helper — build ABI method from ARC-4 signature string
# ─────────────────────────────────────────────────────────────

def make_method(signature):
    return sdk_abi.Method.from_signature(signature)


# ─────────────────────────────────────────────────────────────
# Helper — wait for confirmation
# ─────────────────────────────────────────────────────────────

def wait_confirm(client, txid, rounds=4):
    last = client.status()["last-round"]
    client.status_after_block(last + rounds)
    info = client.pending_transaction_info(txid)
    return info


# ─────────────────────────────────────────────────────────────
# Helper — pretty-print position tuple
# ─────────────────────────────────────────────────────────────

def print_position(pos):
    stake, count, tier_max_draw, outstanding, defaulted, tier, apr_bps, daily_drawn, repay_by = pos
    tier_name = TIER_NAMES.get(int(tier), "Unknown")
    print("    stake_amount   :", stake, "uA")
    print("    payment_count  :", count)
    print("    tier_max_draw  :", tier_max_draw, "uA")
    print("    outstanding    :", outstanding, "uA")
    print("    is_defaulted   :", defaulted)
    print("    tier           :", tier, "(" + tier_name + ")")
    print("    apr_bps        :", apr_bps, "(" + str(int(apr_bps) / 100) + "% APR)")
    print("    daily_drawn    :", daily_drawn, "uA")
    print("    repay_by_round :", repay_by)


# ─────────────────────────────────────────────────────────────
# Main demo
# ─────────────────────────────────────────────────────────────

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_URL)
    params = client.suggested_params()

    print()
    print("=" * 60)
    print("  BLOOPA TESTNET DEMO  🤖")
    print("=" * 60)
    print("  Agent address :", AGENT_ADDR)
    print("  App ID        :", APP_ID)
    print()

    # ── STEP 1: Opt-In (skip if already opted in) ────────────
    print("🔑  STEP 1: Opt-in to Bloopa app...")
    acct_info = client.account_info(AGENT_ADDR)
    already_opted_in = any(
        ls["id"] == APP_ID
        for ls in acct_info.get("apps-local-state", [])
    )
    if already_opted_in:
        print("    Already opted in — skipping.")
    else:
        opt_in_txn = ApplicationOptInTxn(
            sender=AGENT_ADDR,
            sp=params,
            index=APP_ID,
        )
        atc = AtomicTransactionComposer()
        atc.add_transaction(TransactionWithSigner(opt_in_txn, SIGNER))
        result = atc.execute(client, wait_rounds=4)
        print("    TX:", result.tx_ids[0])
        print("    Opted in successfully.")
    print()

    # ── STEP 2: Register (stake 1 ALGO) ──────────────────────
    print("📝  STEP 2: Register agent — staking 1 ALGO...")
    # Check if already registered by reading local state
    acct_info = client.account_info(AGENT_ADDR)
    local_state = {}
    for ls in acct_info.get("apps-local-state", []):
        if ls["id"] == APP_ID:
            for kv in ls.get("key-value", []):
                import base64
                k = base64.b64decode(kv["key"]).decode("utf-8", errors="replace")
                local_state[k] = kv["value"].get("uint", 0)
    stake = local_state.get("stake_amount", 0)
    if stake > 0:
        print(f"    Already registered (stake={stake} uA) — skipping.")
    else:
        from algosdk.logic import get_application_address
        app_address = get_application_address(APP_ID)
        pay_txn = PaymentTxn(
            sender=AGENT_ADDR,
            sp=params,
            receiver=app_address,
            amt=STAKE_AMOUNT,
        )
        atc = AtomicTransactionComposer()
        atc.add_method_call(
            app_id=APP_ID,
            method=make_method("register(pay)void"),
            sender=AGENT_ADDR,
            sp=params,
            signer=SIGNER,
            method_args=[TransactionWithSigner(pay_txn, SIGNER)],
        )
        result = atc.execute(client, wait_rounds=4)
        print("    TX:", result.tx_ids[-1])
        print("    Registered with 1 ALGO stake.")
    print()

    # ── STEP 3: Record 3 payments ─────────────────────────────
    print("💳  STEP 3: Recording 3 off-chain payments...")
    for i in range(1, 4):
        params = client.suggested_params()
        atc = AtomicTransactionComposer()
        atc.add_method_call(
            app_id=APP_ID,
            method=make_method("record_payment(uint64)uint64"),
            sender=AGENT_ADDR,
            sp=params,
            signer=SIGNER,
            method_args=[i * 10_000],
        )
        result = atc.execute(client, wait_rounds=4)
        tier_returned = result.abi_results[0].return_value
        print("    Payment", i, "recorded. Current tier:", tier_returned, "(" + TIER_NAMES.get(int(tier_returned), "?") + ")")
    print()

    # ── STEP 4: Get position ──────────────────────────────────
    print("📊  STEP 4: Checking position after 3 payments...")
    params = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=APP_ID,
        method=make_method("get_position(address)(uint64,uint64,uint64,uint64,uint64,uint64,uint64,uint64,uint64)"),
        sender=AGENT_ADDR,
        sp=params,
        signer=SIGNER,
        method_args=[AGENT_ADDR],
    )
    result = atc.execute(client, wait_rounds=4)
    position = result.abi_results[0].return_value
    print_position(position)
    print()

    # ── STEP 5: Draw 50_000 microALGO ────────────────────────
    print("💸  STEP 5: Drawing 50,000 microALGO (0.05 ALGO)...")
    params = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=APP_ID,
        method=make_method("draw(uint64,byte[32])void"),
        sender=AGENT_ADDR,
        sp=params,
        signer=SIGNER,
        method_args=[DRAW_AMOUNT, DUMMY_ATTESTATION],
    )
    result = atc.execute(client, wait_rounds=4)
    print("    TX:", result.tx_ids[-1])
    print("    Drew 50,000 uA. Funds arriving in agent wallet.")
    print()

    # ── STEP 6: Simulate task execution ──────────────────────
    print("🤖  STEP 6: Agent executing task...")
    print("    task executing...")
    time.sleep(2)
    print("    Task complete. Preparing repayment.")
    print()

    # ── STEP 7: Repay (principal + small buffer for interest) ─
    # Interest at Tier 0: 50_000 * 2400 * 86400 / (10000 * 31536000) ≈ 32 uA
    # We repay principal + 100 uA buffer to be safe
    repay_amount = DRAW_AMOUNT + 100
    print("💰  STEP 7: Repaying", repay_amount, "microALGO (principal + interest)...")
    params = client.suggested_params()
    from algosdk.logic import get_application_address
    app_address = get_application_address(APP_ID)
    repay_pay_txn = PaymentTxn(
        sender=AGENT_ADDR,
        sp=params,
        receiver=app_address,
        amt=repay_amount,
    )
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=APP_ID,
        method=make_method("repay(pay)void"),
        sender=AGENT_ADDR,
        sp=params,
        signer=SIGNER,
        method_args=[TransactionWithSigner(repay_pay_txn, SIGNER)],
    )
    result = atc.execute(client, wait_rounds=4)
    print("    TX:", result.tx_ids[-1])
    print("    Repayment confirmed.")
    print()

    # ── STEP 8: Final get_position ────────────────────────────
    print("📊  STEP 8: Final position after repayment...")
    params = client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=APP_ID,
        method=make_method("get_position(address)(uint64,uint64,uint64,uint64,uint64,uint64,uint64,uint64,uint64)"),
        sender=AGENT_ADDR,
        sp=params,
        signer=SIGNER,
        method_args=[AGENT_ADDR],
    )
    result = atc.execute(client, wait_rounds=4)
    position = result.abi_results[0].return_value
    print_position(position)
    print()

    print("=" * 60)
    print("  DEMO COMPLETE  ✅")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
