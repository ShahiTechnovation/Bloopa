"""
deploy_router.py — Deploy BloopIntentRouter to Algorand testnet.

Usage:
    ADMIN_MNEMONIC="25 words..." BLOOPA_APP_ID=762466410 python contracts/deploy_router.py

Steps:
    1. Compile bloopa_router.py via puyapy to temp dir
    2. Deploy + bootstrap() atomically using ATC (ApplicationCreate + method call)
    3. Fund the Router contract's escrow address (MBR)
    4. Print the new Router App ID and escrow address
    5. Write Router App ID to contracts/router_app_id.txt

Why ATC for deploy:
    puyapy 5.8.0 generates ARC-4 contracts where the create method (bootstrap)
    must be called in the ApplicationCreate transaction itself (method selector
    in ApplicationArgs[0]). Using a bare ApplicationCreateTxn without the
    method selector causes the contract to reject with "err" at pc=179.
    AtomicTransactionComposer with add_method_call(on_complete=NoOpOC) and
    no existing app_id creates the application and calls bootstrap atomically.

Requirements:
    - puyapy >= 5.8.0 (pip install puyapy)
    - Funded testnet account in ADMIN_MNEMONIC
    - BLOOPA_APP_ID set to the Bloopa contract App ID (762466410 on testnet)
"""

import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import algosdk
from algosdk import account, logic, mnemonic
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    AccountTransactionSigner,
)
from algosdk.abi import Method, Contract
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


# ── Step 1: Compile bloopa_router.py ─────────────────────────────────────────

print()
print("=" * 50)
print("STEP 1 — Compiling bloopa_router.py...")
print("=" * 50)

router_py = CONTRACTS_DIR / "bloopa_router.py"

if not router_py.exists():
    print(f"ERROR: {router_py} not found.")
    sys.exit(1)

# puyapy 5.x outputs to <tmpdir>/contracts/BloopIntentRouter.*
# Use a tempdir to avoid stale artifacts from previous compilations
with tempfile.TemporaryDirectory() as tmpdir:
    compiled_ok = False
    teal_source_approval = None
    teal_source_clear    = None

    # Try algokit first
    try:
        res = subprocess.run(
            ["algokit", "compile", "python", str(router_py), "--out-dir", tmpdir],
            capture_output=True, text=True, cwd=str(CONTRACTS_DIR),
        )
        if res.returncode == 0:
            print("  algokit compile: OK")
            compiled_ok = True
        else:
            print(f"  algokit failed (exit {res.returncode}): {res.stderr[:300]}")
    except FileNotFoundError:
        print("  WARNING: algokit not found. Trying puyapy...")

    # Fallback: puyapy
    if not compiled_ok:
        try:
            res = subprocess.run(
                [sys.executable, "-m", "puyapy", str(router_py), "--out-dir", tmpdir],
                capture_output=True, text=True,
            )
            if res.returncode == 0:
                print("  puyapy compile: OK")
                compiled_ok = True
            else:
                print(f"  puyapy failed:\n{res.stderr}")
        except Exception as exc:
            print(f"  puyapy not available: {exc}")

    if not compiled_ok:
        print("\nFATAL: Cannot compile bloopa_router.py.")
        sys.exit(1)

    # Locate TEAL in tmpdir (may be in a contracts/ subdir due to puyapy 5.x)
    approval_candidates = list(Path(tmpdir).rglob("BloopIntentRouter.approval.teal"))
    clear_candidates    = list(Path(tmpdir).rglob("BloopIntentRouter.clear.teal"))
    arc56_candidates    = list(Path(tmpdir).rglob("BloopIntentRouter.arc56.json"))

    if not approval_candidates or not clear_candidates:
        all_files = list(Path(tmpdir).rglob("*"))
        print(f"ERROR: TEAL not found in tmpdir. Files: {[str(f) for f in all_files[:20]]}")
        sys.exit(1)

    approval_path = approval_candidates[0]
    clear_path    = clear_candidates[0]
    print(f"  Approval TEAL: {approval_path.name}  ({approval_path.stat().st_size} bytes)")
    print(f"  Clear TEAL:    {clear_path.name}")

    # Read into memory BEFORE tmpdir is cleaned up
    teal_source_approval = approval_path.read_text()
    teal_source_clear    = clear_path.read_text()

    # Read ARC-56 ABI for method extraction
    arc56_json = None
    if arc56_candidates:
        arc56_json = json.loads(arc56_candidates[0].read_text())

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
    print("STEP 3 — Deploying BloopIntentRouter via ATC...")
    print("=" * 50)

    # Compile TEAL to bytecode via algod
    approval_bytes = compile_teal(algod_client, teal_source_approval)
    clear_bytes    = compile_teal(algod_client, teal_source_clear)

    print(f"  Approval program: {len(approval_bytes)} bytes")
    print(f"  Clear program:    {len(clear_bytes)} bytes")

    # State schema: 4 uint64 + 1 bytes global; 0 local
    from algosdk.transaction import StateSchema
    global_schema = StateSchema(num_uints=4, num_byte_slices=1)
    local_schema  = StateSchema(num_uints=0, num_byte_slices=0)

    # ARC-4 ABI create = require: the ApplicationCreate txn MUST carry the
    # bootstrap(uint64) method selector in ApplicationArgs[0].
    # The AtomicTransactionComposer with app_id=0 creates the application.
    # We pass the ABI method signature directly.
    bootstrap_method = Method.from_signature("bootstrap(uint64)void")

    sp = algod_client.suggested_params()
    sp.fee = sp.min_fee  # standard fee

    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=0,  # 0 = ApplicationCreate
        method=bootstrap_method,
        sender=admin_address,
        sp=sp,
        signer=admin_signer,
        method_args=[BLOOPA_APP_ID],
        on_complete=algosdk.transaction.OnComplete.NoOpOC,
        approval_program=approval_bytes,
        clear_program=clear_bytes,
        global_schema=global_schema,
        local_schema=local_schema,
    )

    print("  Submitting ApplicationCreate + bootstrap()...")
    try:
        result = atc.execute(algod_client, 4)
    except Exception as exc:
        print(f"\nFATAL: Deploy failed: {exc}")
        sys.exit(1)

    deploy_txid = result.tx_ids[0]
    print(f"  Deploy txn: {deploy_txid}")

    # Get App ID from confirmed transaction
    confirmed = algod_client.pending_transaction_info(deploy_txid)
    ROUTER_APP_ID = confirmed.get("application-index")
    if not ROUTER_APP_ID:
        print(f"ERROR: Could not extract App ID from: {confirmed}")
        sys.exit(1)

    print(f"  Deployed & bootstrapped. Router App ID: {ROUTER_APP_ID}")
    ROUTER_ID_FILE.write_text(str(ROUTER_APP_ID))
    print(f"  Router App ID written to {ROUTER_ID_FILE}")

else:
    print(f"  Reusing existing Router App ID: {ROUTER_APP_ID}")

# ── Step 4: Fund Router MBR ───────────────────────────────────────────────────

print()
print("=" * 50)
print("STEP 4 — Funding Router escrow (MBR)...")
print("=" * 50)

from algosdk.transaction import PaymentTxn

ROUTER_ADDRESS = logic.get_application_address(ROUTER_APP_ID)
print(f"  Router address: {ROUTER_ADDRESS}")

# Minimum balance: 100,000 uA base + enough for inner txn fees buffer
MIN_FUND_UA   = 1_000_000  # 1 ALGO
current_bal   = algod_client.account_info(ROUTER_ADDRESS).get("amount", 0)

if current_bal >= MIN_FUND_UA:
    print(f"  Router already funded: {current_bal:,} uA -- skipping.")
else:
    fund_needed = MIN_FUND_UA - current_bal
    sp = algod_client.suggested_params()
    fund_txn = PaymentTxn(
        sender=admin_address,
        sp=sp,
        receiver=ROUTER_ADDRESS,
        amt=fund_needed,
    )
    signed = fund_txn.sign(admin_private_key)
    tx_id  = algod_client.send_transaction(signed)
    wait_for_confirmation(algod_client, tx_id)
    print(f"  Funded Router with {fund_needed:,} uA.")

# ── Step 5: Print deployment summary ─────────────────────────────────────────

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
print(f"Escrow balance:   {final_bal:,} uA ({final_bal / 1_000_000:.6f} ALGO)")
print(f"Explorer:         https://testnet.explorer.perawallet.app/application/{ROUTER_APP_ID}")
print("=" * 50)
print()
print("Next step: set ROUTER_APP_ID in your shell and run the demo:")
print(f"  $env:ROUTER_APP_ID={ROUTER_APP_ID}")
print(f"  python demo/intent_demo.py")
