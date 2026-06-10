"""
x402_demo.py — BloopX402Client live demo against GoPlausible testnet.

Tests the full x402 payment flow:
  1. Verify the GoPlausible endpoint is 402-gated (no payment)
  2. Auto opt-in wallet to USDC ASA 10458941 (if needed)
  3. Auto-swap ALGO → USDC via Tinyman (if needed)
  4. Draw Bloopa credit, sign Algorand payment group, pay via X-PAYMENT header
  5. Receive 200 OK response
  6. Check on-chain Bloopa reputation incremented

Prerequisites:
  pip install "bloopa-sdk[x402]"

Environment variables:
  AGENT_MNEMONIC=word1 word2 ... word25   (25-word Algorand mnemonic)
  BLOOPA_APP_ID=762466410                 (testnet Bloopa contract)
  VENICE_API_KEY=...                      (or ANTHROPIC_API_KEY)
  ORACLE_PROVIDER=venice                  (or anthropic)

The wallet must have:
  - At least 1 ALGO (for transactions + opt-in min balance)
  - The USDC ASA opt-in is done automatically

Get testnet ALGO: https://testnet.algoexplorer.io/dispenser
"""

import os
import sys
import logging

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("x402_demo")

# ── Load environment ──────────────────────────────────────────────────────────

try:
    from dotenv import load_dotenv
    load_dotenv(".bloopa.env")
    load_dotenv()
except ImportError:
    pass  # dotenv optional

AGENT_MNEMONIC = os.environ.get("AGENT_MNEMONIC") or os.environ.get("BLOOPA_MNEMONIC")
BLOOPA_APP_ID = int(os.environ.get("BLOOPA_APP_ID", "762466410"))

if not AGENT_MNEMONIC:
    print("ERROR: Set AGENT_MNEMONIC environment variable (25-word Algorand mnemonic)")
    sys.exit(1)

# ── Imports ───────────────────────────────────────────────────────────────────

try:
    from bloopa_sdk import BloopaCreditAgent, BloopX402Client
    from bloopa_sdk.exceptions import (
        BloopX402SpendLimitExceeded,
        BloopX402PaymentError,
        BloopX402SetupError,
        BloopaCreditDenied,
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Run: pip install \"bloopa-sdk[x402]\"")
    sys.exit(1)

import httpx

# ── GoPlausible testnet endpoints ─────────────────────────────────────────────
ENDPOINTS = {
    "example_resource": "https://example.x402.goplausible.xyz/",
    "weather_api":      "https://x402.goplausible.xyz/examples/weather",
}

FACILITATOR_URL = "https://facilitator.goplausible.xyz"


def separator(title: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print('═' * 60)


def main() -> int:
    """Run the full x402 demo. Returns exit code."""

    separator("STEP 0: Facilitator Health Check")
    try:
        resp = httpx.get(f"{FACILITATOR_URL}/health", timeout=10.0)
        health = resp.json()
        status = health.get("status", "unknown")
        version = health.get("version", "?")
        print(f"✓ Facilitator status: {status}  version: {version}")

        networks = health.get("networks", {})
        testnet_key = "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI="
        testnet_status = networks.get(testnet_key, {}).get("status", "unknown")
        print(f"✓ Algorand Testnet: {testnet_status}")

        if status != "healthy":
            print(f"⚠ Facilitator not healthy: {status}. Continuing anyway...")
    except Exception as exc:
        print(f"⚠ Facilitator health check failed: {exc}. Continuing anyway...")

    separator("STEP 1: Confirm 402 Gate (no payment)")
    for name, url in ENDPOINTS.items():
        try:
            raw = httpx.get(url, timeout=10.0)
            if raw.status_code == 402:
                req_body = raw.json()
                scheme = req_body.get("scheme", "?")
                amount = req_body.get("amount", "?")
                asset = req_body.get("asset", "?")
                network = req_body.get("network", "?")
                print(f"✓ {name}: 402 confirmed")
                print(f"  scheme={scheme}  amount={amount}μ  asset={asset}")
                print(f"  network={network}")
            else:
                print(f"⚠ {name}: Expected 402, got {raw.status_code}")
        except Exception as exc:
            print(f"✗ {name}: Connection error: {exc}")

    separator("STEP 2: Initialise BloopaCreditAgent")
    try:
        agent = BloopaCreditAgent(
            mnemonic_phrase=AGENT_MNEMONIC,
            app_id=BLOOPA_APP_ID,
        )
        print(f"✓ Agent: {agent.address}")

        pos = agent.get_position()
        print(f"  Tier:         {pos['tier']} ({['Fresh','Trusted','Veteran','Elite'][pos['tier']]})")
        print(f"  Payment count: {pos['payment_count']}")
        print(f"  Outstanding:   {pos['outstanding']} μALGO")
    except Exception as exc:
        print(f"✗ Agent init failed: {exc}")
        return 1

    separator("STEP 3: Initialise BloopX402Client (auto opt-in)")
    try:
        client = BloopX402Client(
            agent,
            max_spend_per_call=50_000,   # 0.05 USDC max per call
            auto_opt_in=True,
            auto_swap=True,
        )
        print(f"✓ Client ready: {client}")
        print(f"  ALGO balance:  {client.algo_balance():,} μALGO")
        print(f"  USDC balance:  {client.usdc_balance():,} μUSDC")
    except BloopX402SetupError as exc:
        print(f"✗ Setup error: {exc}")
        print("  Ensure wallet has at least 1 ALGO. Get testnet ALGO:")
        print("  https://testnet.algoexplorer.io/dispenser")
        return 1
    except Exception as exc:
        print(f"✗ Client init failed: {exc}")
        return 1

    separator("STEP 4: Pay-per-call — Example Resource")
    url = ENDPOINTS["example_resource"]
    try:
        print(f"  GET {url}")
        print("  (x402 flow: 402 → Algorand payment → X-PAYMENT header → 200)")

        response = client.get(url)

        print(f"\n✓ Status: {response.status_code}")
        body = response.text[:500]
        print(f"  Body preview:\n{body}")

        # Show post-payment balances
        print(f"\n  ALGO balance after: {client.algo_balance():,} μALGO")
        print(f"  USDC balance after: {client.usdc_balance():,} μUSDC")

    except BloopX402SpendLimitExceeded as exc:
        print(f"✗ Spend limit exceeded: {exc.amount} μUSDC > {exc.limit} μUSDC")
        return 1
    except BloopX402PaymentError as exc:
        print(f"✗ Payment failed: {exc.reason}")
        return 1
    except BloopaCreditDenied as exc:
        print(f"✗ Bloopa credit denied: {exc.reason}")
        return 1
    except Exception as exc:
        print(f"✗ Request failed: {exc}")
        import traceback
        traceback.print_exc()
        return 1

    separator("STEP 5: Pay-per-call — Weather API")
    url = ENDPOINTS["weather_api"]
    try:
        print(f"  GET {url}")
        response = client.get(url)
        print(f"✓ Status: {response.status_code}")
        print(f"  Weather data:\n{response.text[:300]}")
    except Exception as exc:
        print(f"✗ Weather API request failed: {exc}")
        # Non-fatal — some endpoints may not be up

    separator("STEP 6: Bloopa On-Chain Reputation")
    try:
        pos_after = agent.get_position()
        print(f"  Payment count: {pos_after['payment_count']}  (was {pos['payment_count']})")
        print(f"  Tier:          {pos_after['tier']} ({['Fresh','Trusted','Veteran','Elite'][pos_after['tier']]})")
        delta = pos_after['payment_count'] - pos['payment_count']
        if delta > 0:
            print(f"✓ On-chain payment count increased by {delta} ✓")
        else:
            print("  Payment count unchanged (record_payment may have been skipped)")
    except Exception as exc:
        print(f"  Could not read position: {exc}")

    separator("DEMO COMPLETE")
    print("✓ BloopX402Client successfully demonstrated the full x402 flow:")
    print("  402 → Algorand USDC payment → X-PAYMENT header → 200 OK")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
