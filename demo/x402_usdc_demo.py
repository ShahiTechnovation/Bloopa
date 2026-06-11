"""
x402_usdc_demo.py - Full x402 + BloopUSDC credit flow demo.

Demonstrates the complete end-to-end flow:
  1. Agent opts into BloopUSDC contract
  2. Agent registers (stakes 1 ALGO)
  3. Agent draws USDC credit (draw_usdc)
  4. Agent pays a GoPlausible x402-gated API directly (draw_and_pay)
  5. Agent repays USDC debt
  6. Agent's payment_count increments (tier progression)

Usage:
  python demo/x402_usdc_demo.py

Environment (contracts/.env):
  DEPLOYER_MNEMONIC=<25-word mnemonic>

For USDC treasury: get testnet USDC from https://faucet.circle.com/
then run: python contracts/deploy_usdc.py
"""

import base64
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from algosdk import account, mnemonic, transaction
from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk import abi
from algosdk.v2client import algod as algod_module
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "contracts" / ".env")

# ── Configuration ──────────────────────────────────────────────────────────────

ALGOD_SERVER    = "https://testnet-api.algonode.cloud"
USDC_ASA_ID     = 10_458_941      # Circle USDC on Algorand testnet

# Load USDC App ID from deployment file
USDC_APP_ID_FILE = Path(__file__).parent.parent / "contracts" / "usdc_app_id.txt"
if USDC_APP_ID_FILE.exists():
    USDC_APP_ID = int(USDC_APP_ID_FILE.read_text().strip())
else:
    USDC_APP_ID = 764_375_950

DEMO_BYTES32    = bytes(32)       # zero hash used in demo/skip_attestation mode

# ── Load deployer wallet ───────────────────────────────────────────────────────

MNEMONIC = os.environ.get("DEPLOYER_MNEMONIC", "")
if not MNEMONIC:
    print("ERROR: DEPLOYER_MNEMONIC not set in contracts/.env")
    sys.exit(1)

private_key = mnemonic.to_private_key(MNEMONIC)
address     = account.address_from_private_key(private_key)

algod_client = algod_module.AlgodClient("", ALGOD_SERVER)

print("=" * 60)
print("BloopUSDC + x402 Demo")
print("=" * 60)
print(f"Agent address : {address}")
print(f"USDC App ID   : {USDC_APP_ID}")
print(f"USDC ASA ID   : {USDC_ASA_ID}")
print()

# ── Helper: wait for confirmation ─────────────────────────────────────────────


def wait(tx_id: str, rounds: int = 8) -> dict:
    """Wait for a transaction to be confirmed."""
    last = algod_client.status()["last-round"]
    start = last
    while True:
        try:
            info = algod_client.pending_transaction_info(tx_id)
            if info.get("confirmed-round", 0) > 0:
                print(f"  Confirmed round {info['confirmed-round']} | txn: {tx_id}")
                return info
            if info.get("pool-error"):
                raise RuntimeError(f"TX failed: {info['pool-error']}")
        except Exception as e:
            if "not found" not in str(e).lower():
                raise
        algod_client.status_after_block(last + 1)
        last += 1
        if last > start + rounds:
            raise TimeoutError("Confirmation timeout")


# ── Helper: read global state ──────────────────────────────────────────────────


def get_global_state(app_id: int) -> dict:
    """Read global state of an application."""
    app_info = algod_client.application_info(app_id)
    state = {}
    for kv in app_info.get("params", {}).get("global-state", []):
        key   = base64.b64decode(kv["key"]).decode("utf-8", errors="replace")
        value = kv["value"]
        state[key] = value["uint"] if value["type"] == 2 else base64.b64decode(value.get("bytes", ""))
    return state


# ── Helper: read local state ───────────────────────────────────────────────────


def get_local_state(app_id: int, addr: str) -> dict:
    """Read local state for an address in an application."""
    try:
        account_info = algod_client.account_info(addr)
        for app in account_info.get("apps-local-state", []):
            if app["id"] == app_id:
                state = {}
                for kv in app.get("key-value", []):
                    key   = base64.b64decode(kv["key"]).decode("utf-8", errors="replace")
                    value = kv["value"]
                    state[key] = value["uint"] if value["type"] == 2 else base64.b64decode(value.get("bytes", ""))
                return state
        return {}
    except Exception:
        return {}


# ── Helper: check USDC balance ─────────────────────────────────────────────────


def get_usdc_balance(addr: str) -> int:
    """Return micro-USDC balance of an address (0 if not opted in)."""
    try:
        info = algod_client.account_info(addr)
        for a in info.get("assets", []):
            if a.get("asset-id") == USDC_ASA_ID:
                return int(a.get("amount", 0))
        return 0
    except Exception:
        return 0


# ── Helper: is opted into app ─────────────────────────────────────────────────


def is_opted_into_app(app_id: int, addr: str) -> bool:
    """Check if an address is opted into an application."""
    try:
        info = algod_client.account_info(addr)
        for app in info.get("apps-local-state", []):
            if app["id"] == app_id:
                return True
        return False
    except Exception:
        return False


# ── Helper: is opted into ASA ─────────────────────────────────────────────────


def is_opted_into_asa(asa_id: int, addr: str) -> bool:
    """Check if an address is opted into an ASA."""
    try:
        info = algod_client.account_info(addr)
        for a in info.get("assets", []):
            if a.get("asset-id") == asa_id:
                return True
        return False
    except Exception:
        return False


# ── ATC call helper ────────────────────────────────────────────────────────────


def call_method(method_sig: str, args: list, foreign_assets: list = None) -> list:
    """Call a BloopUSDC ABI method and return tx IDs."""
    signer = AccountTransactionSigner(private_key)
    atc    = AtomicTransactionComposer()
    sp     = algod_client.suggested_params()

    kwargs = {
        "app_id": USDC_APP_ID,
        "method": abi.Method.from_signature(method_sig),
        "sender": address,
        "sp": sp,
        "signer": signer,
        "method_args": args,
    }
    if foreign_assets:
        kwargs["foreign_assets"] = foreign_assets

    atc.add_method_call(**kwargs)
    result = atc.execute(algod_client, wait_rounds=6)
    return result.tx_ids


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1: Check global state
# ══════════════════════════════════════════════════════════════════════════════

print("[1] Checking BloopUSDC contract state...")
global_st = get_global_state(USDC_APP_ID)

usdc_asa_id_on_chain = global_st.get("usdc_asa_id", 0)
treasury             = global_st.get("usdc_treasury_balance", 0)
skip_att             = global_st.get("skip_attestation", 1)
total_agents         = global_st.get("total_agents", 0)

print(f"  USDC ASA configured : {usdc_asa_id_on_chain} {'(ok)' if usdc_asa_id_on_chain == USDC_ASA_ID else '(MISMATCH!)'}")
print(f"  USDC treasury       : {treasury} uUSDC (${treasury / 1e6:.4f})")
print(f"  Skip attestation    : {'YES (demo mode)' if skip_att else 'NO (production)'}")
print(f"  Total agents        : {total_agents}")
print()

if usdc_asa_id_on_chain == 0:
    print("ERROR: USDC not configured. Run: python contracts/deploy_usdc.py")
    sys.exit(1)

if treasury == 0:
    print("WARNING: USDC treasury is empty!")
    print("  Get testnet USDC from https://faucet.circle.com/")
    print("  Then run: python contracts/deploy_usdc.py to seed treasury.")
    print("  Continuing in demo mode (will skip actual USDC transfers)...")
    print()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2: Opt agent into USDC ASA (if needed)
# ══════════════════════════════════════════════════════════════════════════════

print("[2] USDC ASA opt-in...")
if not is_opted_into_asa(USDC_ASA_ID, address):
    print(f"  Opting wallet into USDC ASA {USDC_ASA_ID}...")
    sp = algod_client.suggested_params()
    opt_txn = transaction.AssetTransferTxn(
        sender=address,
        sp=sp,
        receiver=address,
        amt=0,
        index=USDC_ASA_ID,
    )
    signed = opt_txn.sign(private_key)
    tx_id  = algod_client.send_transaction(signed)
    wait(tx_id)
else:
    print(f"  Already opted into USDC ASA {USDC_ASA_ID}")

agent_usdc = get_usdc_balance(address)
print(f"  Agent USDC balance: {agent_usdc} uUSDC (${agent_usdc / 1e6:.4f})")
print()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3: Opt agent into BloopUSDC contract
# ══════════════════════════════════════════════════════════════════════════════

print("[3] BloopUSDC contract opt-in...")
if not is_opted_into_app(USDC_APP_ID, address):
    sp = algod_client.suggested_params()
    opt_txn = transaction.ApplicationOptInTxn(
        sender=address,
        sp=sp,
        index=USDC_APP_ID,
    )
    signed = opt_txn.sign(private_key)
    tx_id  = algod_client.send_transaction(signed)
    wait(tx_id)
    print(f"  Opted in to BloopUSDC app {USDC_APP_ID}")
else:
    print(f"  Already opted in to BloopUSDC app {USDC_APP_ID}")
print()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4: Register agent (stake 1 ALGO) if not already registered
# ══════════════════════════════════════════════════════════════════════════════

print("[4] Agent registration...")
local_st    = get_local_state(USDC_APP_ID, address)
stake_amt   = local_st.get("stake_amount", 0)

if stake_amt == 0:
    print("  Registering agent with 1 ALGO stake...")

    signer  = AccountTransactionSigner(private_key)
    atc_reg = AtomicTransactionComposer()
    sp      = algod_client.suggested_params()

    # The payment txn (stake) must be in the same group as register()
    stake_txn = transaction.PaymentTxn(
        sender=address,
        sp=sp,
        receiver=__import__("algosdk").logic.get_application_address(USDC_APP_ID),
        amt=1_000_000,  # 1 ALGO
    )

    atc_reg.add_method_call(
        app_id=USDC_APP_ID,
        method=abi.Method.from_signature("register(pay)void"),
        sender=address,
        sp=sp,
        signer=signer,
        method_args=[TransactionWithSigner(stake_txn, signer)],
    )
    result = atc_reg.execute(algod_client, wait_rounds=6)
    print(f"  Registered! txn: {result.tx_ids[0]}")
    local_st = get_local_state(USDC_APP_ID, address)
else:
    print(f"  Already registered (stake: {stake_amt} uALGO = {stake_amt / 1e6:.4f} ALGO)")

payment_count = local_st.get("payment_count", 0)
outstanding   = local_st.get("usdc_outstanding", 0)

# Determine tier
if payment_count >= 100:
    tier, tier_name = 3, "Elite"
elif payment_count >= 50:
    tier, tier_name = 2, "Veteran"
elif payment_count >= 10:
    tier, tier_name = 1, "Trusted"
else:
    tier, tier_name = 0, "Fresh"

print(f"  Payment count : {payment_count}")
print(f"  Current tier  : {tier} ({tier_name})")
print(f"  Outstanding   : {outstanding} uUSDC")
print()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 5: Draw USDC credit
# ══════════════════════════════════════════════════════════════════════════════

DRAW_CAPS = [100_000, 500_000, 2_000_000, 5_000_000]  # per tier
DRAW_AMOUNT = min(DRAW_CAPS[tier], 50_000)  # draw 0.05 USDC (safe small amount)

print(f"[5] Drawing {DRAW_AMOUNT} uUSDC credit (${DRAW_AMOUNT / 1e6:.4f} USDC)...")

if outstanding > 0:
    print(f"  Skipping draw - agent has {outstanding} uUSDC outstanding debt.")
    print("  (Repay first to draw again)")
elif treasury == 0:
    print("  Skipping draw - treasury is empty (no USDC to lend).")
    print("  Fund treasury at https://faucet.circle.com/ then re-run.")
else:
    try:
        tx_ids = call_method(
            "draw_usdc(uint64,byte[32])void",
            args=[DRAW_AMOUNT, DEMO_BYTES32],
            foreign_assets=[USDC_ASA_ID],
        )
        print(f"  Drew {DRAW_AMOUNT} uUSDC! txn: {tx_ids[0]}")

        local_st    = get_local_state(USDC_APP_ID, address)
        outstanding = local_st.get("usdc_outstanding", 0)
        agent_usdc  = get_usdc_balance(address)
        print(f"  Agent USDC balance : {agent_usdc} uUSDC")
        print(f"  Outstanding debt   : {outstanding} uUSDC")
    except Exception as e:
        print(f"  Draw failed: {e}")

print()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 6: x402 payment demo — draw_and_pay to merchant
# ══════════════════════════════════════════════════════════════════════════════

print("[6] x402 draw_and_pay demo...")
print("    This method atomically draws USDC credit and forwards it to a payee.")
print("    In a real x402 flow this payee would be the GoPlausible facilitator")
print("    or merchant address from the HTTP 402 response.")
print()

# Use the deployer address as the demo "merchant" payee
DEMO_PAYEE = address  # in real x402 this is the merchant address from 402 body
PAY_AMOUNT = 1_000   # 0.001 USDC ($0.001) - tiny x402 payment

local_st    = get_local_state(USDC_APP_ID, address)
outstanding = local_st.get("usdc_outstanding", 0)

if outstanding > 0:
    print(f"  Outstanding debt: {outstanding} uUSDC - skipping draw_and_pay.")
elif treasury == 0:
    print("  Treasury empty - skipping draw_and_pay demo.")
else:
    try:
        signer     = AccountTransactionSigner(private_key)
        atc_pay    = AtomicTransactionComposer()
        sp         = algod_client.suggested_params()

        atc_pay.add_method_call(
            app_id=USDC_APP_ID,
            method=abi.Method.from_signature("draw_and_pay(uint64,address,byte[32])void"),
            sender=address,
            sp=sp,
            signer=signer,
            method_args=[PAY_AMOUNT, DEMO_PAYEE, DEMO_BYTES32],
            foreign_assets=[USDC_ASA_ID],
        )
        result = atc_pay.execute(algod_client, wait_rounds=6)
        print(f"  draw_and_pay({PAY_AMOUNT} uUSDC -> {DEMO_PAYEE[:20]}...) OK")
        print(f"  txn: {result.tx_ids[0]}")

        local_st    = get_local_state(USDC_APP_ID, address)
        outstanding = local_st.get("usdc_outstanding", 0)
        print(f"  Outstanding after draw_and_pay: {outstanding} uUSDC")
    except Exception as e:
        print(f"  draw_and_pay failed: {e}")

print()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 7: Repay USDC debt
# ══════════════════════════════════════════════════════════════════════════════

print("[7] Repaying USDC debt...")

local_st    = get_local_state(USDC_APP_ID, address)
outstanding = local_st.get("usdc_outstanding", 0)
agent_usdc  = get_usdc_balance(address)

if outstanding == 0:
    print("  No outstanding debt - skipping repayment.")
elif agent_usdc < outstanding:
    print(f"  Insufficient USDC: need {outstanding}, have {agent_usdc}.")
    print("  Get more USDC from https://faucet.circle.com/")
else:
    print(f"  Repaying {outstanding} uUSDC (${outstanding / 1e6:.6f})...")

    signer      = AccountTransactionSigner(private_key)
    atc_repay   = AtomicTransactionComposer()
    sp          = algod_client.suggested_params()
    app_address = __import__("algosdk").logic.get_application_address(USDC_APP_ID)

    # axfer: agent -> contract
    axfer_txn = transaction.AssetTransferTxn(
        sender=address,
        sp=sp,
        receiver=app_address,
        amt=outstanding,
        index=USDC_ASA_ID,
    )

    atc_repay.add_method_call(
        app_id=USDC_APP_ID,
        method=abi.Method.from_signature("repay_usdc(axfer)void"),
        sender=address,
        sp=sp,
        signer=signer,
        method_args=[TransactionWithSigner(axfer_txn, signer)],
        foreign_assets=[USDC_ASA_ID],
    )
    result = atc_repay.execute(algod_client, wait_rounds=6)
    print(f"  Repaid! txn: {result.tx_ids[0]}")

    local_st      = get_local_state(USDC_APP_ID, address)
    payment_count = local_st.get("payment_count", 0)
    outstanding   = local_st.get("usdc_outstanding", 0)
    print(f"  Outstanding after repay : {outstanding} uUSDC")
    print(f"  Payment count now       : {payment_count}")

print()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 8: Read final position
# ══════════════════════════════════════════════════════════════════════════════

print("[8] Final position...")

global_st   = get_global_state(USDC_APP_ID)
local_st    = get_local_state(USDC_APP_ID, address)
agent_usdc  = get_usdc_balance(address)
treasury    = global_st.get("usdc_treasury_balance", 0)

payment_count = local_st.get("payment_count", 0)
outstanding   = local_st.get("usdc_outstanding", 0)
stake_amt     = local_st.get("stake_amount", 0)

if payment_count >= 100:
    tier, tier_name = 3, "Elite"
elif payment_count >= 50:
    tier, tier_name = 2, "Veteran"
elif payment_count >= 10:
    tier, tier_name = 1, "Trusted"
else:
    tier, tier_name = 0, "Fresh"

draw_caps = [100_000, 500_000, 2_000_000, 5_000_000]
daily_caps = [500_000, 2_000_000, 10_000_000, 25_000_000]

print(f"  Stake       : {stake_amt} uALGO ({stake_amt / 1e6:.4f} ALGO)")
print(f"  Payments    : {payment_count}")
print(f"  Tier        : {tier} - {tier_name}")
print(f"  Draw cap    : {draw_caps[tier]} uUSDC (${draw_caps[tier]/1e6:.2f})")
print(f"  Daily cap   : {daily_caps[tier]} uUSDC (${daily_caps[tier]/1e6:.2f})")
print(f"  Outstanding : {outstanding} uUSDC")
print(f"  Wallet USDC : {agent_usdc} uUSDC (${agent_usdc / 1e6:.4f})")
print(f"  Treasury    : {treasury} uUSDC (${treasury / 1e6:.4f})")
print()

print("=" * 60)
print("BloopUSDC Demo Complete!")
print("=" * 60)
print()
print("x402 Payment Flow Summary:")
print("  1. AI agent receives HTTP 402 from API server")
print("  2. Server sends payment requirements:")
print(f"     amount: 1000 uUSDC, payTo: <merchant>, asset: {USDC_ASA_ID}")
print("  3. Agent calls BloopUSDC.draw_and_pay(1000, merchant, hash)")
print("  4. Contract forwards 1000 uUSDC to merchant atomically")
print("  5. Agent has 1000+interest uUSDC outstanding debt")
print("  6. Agent retries API request with X-PAYMENT header")
print("  7. GoPlausible facilitator verifies on-chain payment")
print("  8. Server returns HTTP 200 with data")
print("  9. Agent later repays via BloopUSDC.repay_usdc(axfer)")
print(" 10. payment_count++ -> tier advancement")
print()
print(f"Contract explorer: https://testnet.explorer.perawallet.app/application/{USDC_APP_ID}/")
