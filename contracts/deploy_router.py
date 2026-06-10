"""
deploy_router.py — Deploy BloopIntentRouter to Algorand testnet.

Usage:
    ADMIN_MNEMONIC="25 words..." BLOOPA_APP_ID=762466410 python contracts/deploy_router.py

Steps:
    1. Compile bloopa_router.py via algokit CLI (subprocess)
    2. Deploy using algosdk (ApplicationCreateTxn)
    3. Call bootstrap(bloopa_app_id) immediately after deploy
    4. Fund the Router contract's escrow address (MBR)
    5. Print the new Router App ID and escrow address
    6. Write Router App ID to contracts/router_app_id.txt

Requirements:
    - algokit CLI installed (pip install algokit)
    - Funded testnet account in ADMIN_MNEMONIC
    - BLOOPA_APP_ID set to the Bloopa contract App ID (762466410 on testnet)
"""

import base64
import os
import subprocess
import sys
from pathlib import Path

import algosdk
from algosdk import account, logic, mnemonic, transaction
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    AccountTransactionSigner,
    TransactionWithSigner,
)
from algosdk.abi import Method
from algosdk.v2client import algod
from dotenv import load_dotenv

# ── Load environment ──────────────────────────────────────────────────────────

CONTRACTS_DIR = Path(__file__).parent

load_dotenv(CONTRACTS_DIR / ".env")

ADMIN_MNEMONIC = os.environ.get("ADMIN_MNEMONIC", "")
BLOOPA_APP_ID  = int(os.environ.get("BLOOPA_APP_ID", "762466410"))

if not ADMIN_MNEMONIC:
    print("ERROR: ADMIN_MNEMONIC environment variable not set.")
    print("       Set it to a funded testnet wallet mnemonic (25 words).")
    sys.exit(1)

admin_private_key = mnemonic.to_private_key(ADMIN_MNEMONIC)
admin_address     = account.address_from_private_key(admin_private_key)
admin_signer      = AccountTransactionSigner(admin_private_key)

print(f"Admin:        {admin_address}")
print(f"Bloopa App:   {BLOOPA_APP_ID}")

# ── Algod client ──────────────────────────────────────────────────────────────

ALGOD_URL   = os.environ.get("ALGOD_URL", "https://testnet-api.algonode.cloud")
ALGOD_TOKEN = ""

algod_client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_URL)

try:
    status = algod_client.status()
    print(f"Connected to testnet. Round: {status['last-round']}")
except Exception as exc:
    print(f"ERROR: Cannot connect to algod: {exc}")
    sys.exit(1)

# ── Helpers ───────────────────────────────────────────────────────────────────


def wait_for_confirmation(client: algod.AlgodClient, tx_id: str, max_rounds: int = 10) -> dict:
    """Wait until a transaction is confirmed."""
    last_round = client.status()["last-round"]
    start = last_round
    while True:
        try:
            result = client.pending_transaction_info(tx_id)
            if result.get("confirmed-round", 0) > 0:
                print(f"  Confirmed in round {result['confirmed-round']}")
                return result
            if result.get("pool-error"):
                raise Exception(f"Transaction failed: {result['pool-error']}")
        except Exception as exc:
            if "not found" not in str(exc).lower():
                raise
        client.status_after_block(last_round + 1)
        last_round += 1
        if last_round > start + max_rounds:
            raise TimeoutError(f"Confirmation timeout after {max_rounds} rounds")


def compile_teal(client: algod.AlgodClient, teal_source: str) -> bytes:
    """Compile TEAL source to AVM bytecode via algod."""
    result = client.compile(teal_source)
    return base64.b64decode(result["result"])


# ── Step 1: Compile bloopa_router.py via algokit ─────────────────────────────

print()
print("=" * 50)
print("STEP 1 — Compiling bloopa_router.py...")
print("=" * 50)

router_py   = CONTRACTS_DIR / "bloopa_router.py"
approval_teal = CONTRACTS_DIR / "BloopIntentRouter.approval.teal"
clear_teal    = CONTRACTS_DIR / "BloopIntentRouter.clear.teal"

if not router_py.exists():
    print(f"ERROR: {router_py} not found.")
    print("       Create contracts/bloopa_router.py first.")
    sys.exit(1)

# Try algokit compile
compiled_ok = False

try:
    result = subprocess.run(
        ["algokit", "compile", "python", str(router_py)],
        capture_output=True,
        text=True,
        cwd=str(CONTRACTS_DIR),
    )
    if result.returncode == 0:
        print("  algokit compile: OK")
        print(result.stdout.strip())
        compiled_ok = True
    else:
        print(f"  algokit compile failed (exit {result.returncode}):")
        print(result.stderr)
except FileNotFoundError:
    print("  WARNING: algokit not found in PATH.")
    print("           Install with: pip install algokit")
    print("           Trying puyapy directly...")

# Fallback: try puyapy
if not compiled_ok:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "puyapy", str(router_py), "--out-dir", str(CONTRACTS_DIR)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("  puyapy compile: OK")
            compiled_ok = True
        else:
            print(f"  puyapy compile failed:")
            print(result.stderr)
    except Exception as exc:
        print(f"  puyapy not available: {exc}")

if not compiled_ok:
    print()
    print("FATAL: Cannot compile bloopa_router.py.")
    print("Fix compilation errors and retry.")
    sys.exit(1)

# ── Locate TEAL artifacts ─────────────────────────────────────────────────────

# algokit may output to a subdirectory; search for it
teal_candidates = list(CONTRACTS_DIR.rglob("BloopIntentRouter.approval.teal"))
clear_candidates = list(CONTRACTS_DIR.rglob("BloopIntentRouter.clear.teal"))

if not teal_candidates:
    # Fallback: look for any approval.teal
    teal_candidates = list(CONTRACTS_DIR.rglob("*router*.approval.teal"))
    clear_candidates = list(CONTRACTS_DIR.rglob("*router*.clear.teal"))

if not teal_candidates or not clear_candidates:
    print("ERROR: Could not find compiled TEAL artifacts.")
    print(f"       Searched in: {CONTRACTS_DIR}")
    print("       Expected: BloopIntentRouter.approval.teal and BloopIntentRouter.clear.teal")
    sys.exit(1)

approval_path = teal_candidates[0]
clear_path    = clear_candidates[0]
print(f"  Approval TEAL: {approval_path}")
print(f"  Clear TEAL:    {clear_path}")

approval_source = approval_path.read_text()
clear_source    = clear_path.read_text()

# ── Step 2: Check for existing Router deployment ──────────────────────────────

print()
print("=" * 50)
print("STEP 2 — Checking for existing Router deployment...")
print("=" * 50)

ROUTER_ID_FILE = CONTRACTS_DIR / "router_app_id.txt"
ROUTER_APP_ID  = None

if ROUTER_ID_FILE.exists():
    raw = ROUTER_ID_FILE.read_text().strip()
    if raw:
        try:
            existing_id = int(raw)
            info = algod_client.application_info(existing_id)
            if not info.get("deleted", False):
                print(f"  Existing Router App ID: {existing_id} (still live)")
                ROUTER_APP_ID = existing_id
            else:
                print(f"  App {existing_id} deleted. Redeploying.")
        except Exception:
            print(f"  App ID {raw} not found on-chain. Redeploying.")

# ── Step 3: Deploy Router contract ───────────────────────────────────────────

if ROUTER_APP_ID is None:
    print()
    print("=" * 50)
    print("STEP 3 — Deploying BloopIntentRouter...")
    print("=" * 50)

    approval_bytes = compile_teal(algod_client, approval_source)
    clear_bytes    = compile_teal(algod_client, clear_source)

    print(f"  Approval program: {len(approval_bytes)} bytes")
    print(f"  Clear program:    {len(clear_bytes)} bytes")

    # State schema:
    # Global: 4 × uint64 (bloopa_app_id, total_intents, router_treasury, is_live)
    #         1 × bytes (admin as Account)
    # Local: none (no OptIn required)
    global_schema = transaction.StateSchema(num_uints=4, num_byte_slices=1)
    local_schema  = transaction.StateSchema(num_uints=0, num_byte_slices=0)

    sp = algod_client.suggested_params()
    create_txn = transaction.ApplicationCreateTxn(
        sender=admin_address,
        sp=sp,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval_bytes,
        clear_program=clear_bytes,
        global_schema=global_schema,
        local_schema=local_schema,
    )

    signed_txn = create_txn.sign(admin_private_key)
    tx_id      = algod_client.send_transaction(signed_txn)
    print(f"  Deploy txn sent: {tx_id}")

    result       = wait_for_confirmation(algod_client, tx_id)
    ROUTER_APP_ID = result["application-index"]
    print(f"  Deployed. Router App ID: {ROUTER_APP_ID}")

    # Save immediately
    ROUTER_ID_FILE.write_text(str(ROUTER_APP_ID))
    print(f"  Router App ID written to {ROUTER_ID_FILE}")

else:
    print(f"  Reusing existing Router App ID: {ROUTER_APP_ID}")

# ── Step 4: Call bootstrap() ──────────────────────────────────────────────────

print()
print("=" * 50)
print("STEP 4 — Bootstrapping Router...")
print("=" * 50)

ROUTER_ADDRESS = logic.get_application_address(ROUTER_APP_ID)
print(f"  Router address: {ROUTER_ADDRESS}")

# Check if already bootstrapped (is_live > 0 means bootstrapped)
try:
    app_info    = algod_client.application_info(ROUTER_APP_ID)
    global_state = {
        base64.b64decode(kv["key"]).decode("utf-8", errors="replace"): kv["value"]
        for kv in app_info.get("params", {}).get("global-state", [])
    }
    is_live = global_state.get("is_live", {}).get("uint", 0)
    if is_live == 1:
        print("  Already bootstrapped — skipping.")
    else:
        raise ValueError("not_bootstrapped")
except Exception:
    # Bootstrap the contract
    sp = algod_client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=ROUTER_APP_ID,
        method=Method.from_signature("bootstrap(uint64)void"),
        sender=admin_address,
        sp=sp,
        signer=admin_signer,
        method_args=[BLOOPA_APP_ID],
    )
    result = atc.execute(algod_client, 4)
    print(f"  bootstrap() txn: {result.tx_ids[0]}")
    print(f"  Router is now live. bloopa_app_id = {BLOOPA_APP_ID}")

# ── Step 5: Fund Router MBR ───────────────────────────────────────────────────

print()
print("=" * 50)
print("STEP 5 — Funding Router escrow (MBR)...")
print("=" * 50)

# Minimum balance for the Router contract:
# Base MBR: 100,000 μA
# Box storage MBR will be covered per-intent by the lock_intent payment
# We fund 1 ALGO for MBR + inner txn fees buffer
MIN_FUND_UA   = 1_000_000  # 1 ALGO
current_bal   = algod_client.account_info(ROUTER_ADDRESS).get("amount", 0)

if current_bal >= MIN_FUND_UA:
    print(f"  Router already funded: {current_bal:,} \u03bcA — skipping.")
else:
    fund_needed = MIN_FUND_UA - current_bal
    sp = algod_client.suggested_params()
    fund_txn = transaction.PaymentTxn(
        sender=admin_address,
        sp=sp,
        receiver=ROUTER_ADDRESS,
        amt=fund_needed,
    )
    signed = fund_txn.sign(admin_private_key)
    tx_id  = algod_client.send_transaction(signed)
    wait_for_confirmation(algod_client, tx_id)
    print(f"  Funded Router with {fund_needed:,} \u03bcA.")

# ── Step 6: Print deployment summary ─────────────────────────────────────────

final_bal = algod_client.account_info(ROUTER_ADDRESS).get("amount", 0)

print()
print("=" * 50)
print("ROUTER DEPLOYMENT SUMMARY")
print("=" * 50)
print(f"Network:          TESTNET")
print(f"Router App ID:    {ROUTER_APP_ID}")
print(f"Router Address:   {ROUTER_ADDRESS}")
print(f"Bloopa App ID:    {BLOOPA_APP_ID}")
print(f"Admin:            {admin_address}")
print(f"Escrow balance:   {final_bal:,} \u03bcA ({final_bal / 1_000_000:.6f} ALGO)")
print(f"Explorer:         https://testnet.algoexplorer.io/application/{ROUTER_APP_ID}")
print("=" * 50)
print()
print("Next step: set ROUTER_APP_ID in your shell and run the demo:")
print(f"  export ROUTER_APP_ID={ROUTER_APP_ID}")
print(f"  python demo/intent_demo.py")
