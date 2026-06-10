"""
tests/test_oracle.py — Offline unit tests for the Bloopa SDK RiskOracle.

Runs without network access. The Venice API and algod client are fully mocked.
All tests use ORACLE_PROVIDER=venice (the default) unless explicitly testing
the Anthropic path.

Tests:
  1. PASS — All 4 criteria satisfied (Venice path).
  2. FAIL criterion 3 — outstanding_microalgo > 0 (loan stacking, Venice path).
  3. Pre-gate denial — amount exceeds tier cap, oracle never called.
  4. FAIL criterion 4 — high-risk task (Venice path).
  5. Interest formula verification.
  6. Anthropic provider path — _anthropic_client used instead of _openai_client.

Run:
    python tests/test_oracle.py
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bloopa_sdk.oracle import CriteriaEvaluation, RiskDecision, RiskOracle
from bloopa_sdk.exceptions import BloopaCreditDenied, BloopaCreditError


# ──────────────────────────────────────────────────────────────────────────────
# Shared constants
# ──────────────────────────────────────────────────────────────────────────────

FAKE_ROUND = 42_000_000
FAKE_SENDER = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ"
FAKE_HASH = bytes(32)


# ──────────────────────────────────────────────────────────────────────────────
# Mock factory helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_mock_algod(current_round: int = FAKE_ROUND) -> MagicMock:
    """Return a mock AlgodClient that reports a fixed round."""
    mock_algod = MagicMock()
    mock_algod.status.return_value = {"last-round": current_round}
    return mock_algod


def make_venice_approved() -> MagicMock:
    """Build a mock Venice chat.completions.create() response — all criteria pass."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "criterion_1_passed": True,
        "criterion_2_passed": True,
        "criterion_3_passed": True,
        "criterion_4_passed": True,
        "overall_approved": True,
        "task_risk_level": "low",
        "denial_reason": "",
        "risk_summary": "Low-risk deterministic API call with positive ROI.",
    })
    return mock_response


def make_venice_denied(failing_criterion: int, reason: str, risk_level: str = "low") -> MagicMock:
    """Build a mock Venice response for a denied draw.

    Args:
        failing_criterion: Criterion index (1-4) to mark as False.
        reason: Denial reason string.
        risk_level: task_risk_level value.

    Returns:
        MagicMock mimicking an OpenAI chat completion response.
    """
    data = {
        "criterion_1_passed": True,
        "criterion_2_passed": True,
        "criterion_3_passed": True,
        "criterion_4_passed": True,
        "overall_approved": False,
        "task_risk_level": risk_level,
        "denial_reason": reason,
        "risk_summary": f"Criterion {failing_criterion} failed.",
    }
    data[f"criterion_{failing_criterion}_passed"] = False
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(data)
    return mock_response


# ──────────────────────────────────────────────────────────────────────────────
# Test 1 — All criteria pass (Venice path)
# ──────────────────────────────────────────────────────────────────────────────

class TestRiskOraclePass(unittest.TestCase):
    """Test case 1: all 4 criteria pass, RiskDecision is returned."""

    def setUp(self) -> None:
        os.environ["ORACLE_PROVIDER"] = "venice"
        os.environ["VENICE_API_KEY"] = "sk-test-venice"
        self.mock_algod = _make_mock_algod()

    def test_all_criteria_pass(self) -> None:
        """All 4 criteria satisfied — should return an approved RiskDecision."""
        with patch("bloopa_sdk.oracle.OpenAI") as mock_openai_class:
            mock_instance = MagicMock()
            mock_openai_class.return_value = mock_instance
            mock_instance.chat.completions.create.return_value = make_venice_approved()

            oracle = RiskOracle(algod_client=self.mock_algod, demo_mode=True)

            decision = oracle.evaluate(
                agent_address=FAKE_SENDER,
                amount_microalgo=50_000,
                payment_count=5,
                outstanding_microalgo=0,
                task_description="Fetch current ETH/USD price from CoinGecko public API.",
                expected_return_microalgo=80_000,
                estimated_task_rounds=120,
            )

        self.assertIsInstance(decision, RiskDecision)
        self.assertTrue(decision.approved)
        self.assertEqual(decision.amount_microalgo, 50_000)
        self.assertEqual(decision.tier, 0)           # payment_count=5, Tier 0
        self.assertEqual(decision.apr_bps, 2400)     # Tier 0 APR
        self.assertIsInstance(decision.interest_microalgo, int)
        self.assertGreaterEqual(decision.interest_microalgo, 0)
        self.assertEqual(
            decision.total_repayable,
            decision.amount_microalgo + decision.interest_microalgo,
        )
        self.assertEqual(decision.attestation_hash, FAKE_HASH)
        self.assertEqual(decision.current_round, FAKE_ROUND)
        self.assertTrue(decision.criteria.overall_approved)

        print("\n✅  TEST 1 PASSED — All criteria met")
        print(f"    Tier:              {decision.tier} (Fresh)")
        print(f"    Amount:            {decision.amount_microalgo} microALGO")
        print(f"    Interest:          {decision.interest_microalgo} microALGO")
        print(f"    Total repayable:   {decision.total_repayable} microALGO")
        print(f"    APR:               {decision.apr_bps} bps ({decision.apr_bps / 100:.0f}%)")
        print(f"    Risk summary:      {decision.criteria.risk_summary}")


# ──────────────────────────────────────────────────────────────────────────────
# Test 2 — Criterion 3 fails (outstanding debt)
# ──────────────────────────────────────────────────────────────────────────────

class TestRiskOracleFailCriterion3(unittest.TestCase):
    """Test case 2: criterion 3 fails because outstanding > 0."""

    def setUp(self) -> None:
        os.environ["ORACLE_PROVIDER"] = "venice"
        os.environ["VENICE_API_KEY"] = "sk-test-venice"
        self.mock_algod = _make_mock_algod()

    def test_outstanding_debt_denied(self) -> None:
        """Agent has 45000 microALGO outstanding — criterion 3 should fail."""
        denial_msg = (
            "Criterion 3 failed: agent has 45000 microALGO outstanding debt. "
            "Loan stacking is not permitted."
        )

        with patch("bloopa_sdk.oracle.OpenAI") as mock_openai_class:
            mock_instance = MagicMock()
            mock_openai_class.return_value = mock_instance
            mock_instance.chat.completions.create.return_value = make_venice_denied(
                3, denial_msg
            )

            oracle = RiskOracle(algod_client=self.mock_algod, demo_mode=True)

            with self.assertRaises(BloopaCreditDenied) as ctx:
                oracle.evaluate(
                    agent_address=FAKE_SENDER,
                    amount_microalgo=50_000,
                    payment_count=5,
                    outstanding_microalgo=45_000,
                    task_description="Fetch current ETH/USD price from CoinGecko.",
                    expected_return_microalgo=80_000,
                    estimated_task_rounds=120,
                )

        exc = ctx.exception
        self.assertIsInstance(exc, BloopaCreditDenied)
        self.assertIn("Criterion 3", exc.reason)
        self.assertFalse(exc.criteria_results.get("overall_approved", True))
        self.assertFalse(exc.criteria_results.get("criterion_3_passed", True))

        print("\n❌  TEST 2 PASSED (denial expected) — Criterion 3 failed")
        print(f"    Denial reason: {exc.reason}")
        for key, val in exc.criteria_results.items():
            print(f"      {key}: {val}")


# ──────────────────────────────────────────────────────────────────────────────
# Test 3 — Pre-gate denial (tier cap exceeded, oracle not called)
# ──────────────────────────────────────────────────────────────────────────────

class TestTierCapPreGate(unittest.TestCase):
    """Test case 3: amount exceeds tier cap — denied before oracle is called."""

    def setUp(self) -> None:
        os.environ["ORACLE_PROVIDER"] = "venice"
        os.environ["VENICE_API_KEY"] = "sk-test-venice"
        self.mock_algod = _make_mock_algod()

    def test_exceeds_tier_cap_denied_before_oracle(self) -> None:
        """Amount 200_000 > Tier 0 cap 100_000 — should fail before calling oracle."""
        with patch("bloopa_sdk.oracle.OpenAI") as mock_openai_class:
            mock_instance = MagicMock()
            mock_openai_class.return_value = mock_instance

            oracle = RiskOracle(algod_client=self.mock_algod, demo_mode=True)

            with self.assertRaises(BloopaCreditDenied) as ctx:
                oracle.evaluate(
                    agent_address=FAKE_SENDER,
                    amount_microalgo=200_000,   # > TIER_0_MAX_DRAW = 100_000
                    payment_count=0,            # Tier 0
                    outstanding_microalgo=0,
                    task_description="Some task",
                    expected_return_microalgo=300_000,
                    estimated_task_rounds=100,
                )

        # Venice must NOT have been called
        mock_instance.chat.completions.create.assert_not_called()

        exc = ctx.exception
        self.assertIn("100_000", exc.reason.replace("100000", "100_000"))
        self.assertEqual(exc.criteria_results, {})

        print("\n⛔  TEST 3 PASSED (pre-gate denial) — Tier cap exceeded before oracle")
        print(f"    Denial reason: {exc.reason}")


# ──────────────────────────────────────────────────────────────────────────────
# Test 4 — Criterion 4 fails (high-risk task)
# ──────────────────────────────────────────────────────────────────────────────

class TestRiskOracleFailCriterion4(unittest.TestCase):
    """Test case 4: criterion 4 fails — speculative/high-risk task denied."""

    def setUp(self) -> None:
        os.environ["ORACLE_PROVIDER"] = "venice"
        os.environ["VENICE_API_KEY"] = "sk-test-venice"
        self.mock_algod = _make_mock_algod()

    def test_high_risk_task_denied(self) -> None:
        """Critical-risk speculative arbitrage task — criterion 4 must fail."""
        denial_msg = (
            "Criterion 4 failed: task risk level is 'critical' — speculative "
            "arbitrage on unaudited contracts is never approved."
        )

        with patch("bloopa_sdk.oracle.OpenAI") as mock_openai_class:
            mock_instance = MagicMock()
            mock_openai_class.return_value = mock_instance
            mock_instance.chat.completions.create.return_value = make_venice_denied(
                4, denial_msg, risk_level="critical"
            )

            oracle = RiskOracle(algod_client=self.mock_algod, demo_mode=True)

            with self.assertRaises(BloopaCreditDenied) as ctx:
                oracle.evaluate(
                    agent_address=FAKE_SENDER,
                    amount_microalgo=50_000,
                    payment_count=21,
                    outstanding_microalgo=0,
                    task_description="Speculative arbitrage on unaudited DEX contracts",
                    expected_return_microalgo=80_000,
                    estimated_task_rounds=120,
                )

        exc = ctx.exception
        self.assertFalse(exc.criteria_results.get("criterion_4_passed", True))
        self.assertEqual(exc.criteria_results.get("task_risk_level"), "critical")

        print("\n🚫  TEST 4 PASSED (denial expected) — Criterion 4 failed (critical risk)")
        print(f"    Denial reason: {exc.reason}")


# ──────────────────────────────────────────────────────────────────────────────
# Test 5 — Interest formula matches on-chain formula
# ──────────────────────────────────────────────────────────────────────────────

class TestInterestFormula(unittest.TestCase):
    """Test case 5: calculate_interest must match the exact AVM formula."""

    def test_interest_formula(self) -> None:
        """Interest calculation must match (amount * APR_bps * DAY) // (10000 * YEAR)."""
        from bloopa_sdk.criteria import (
            calculate_interest, TIER_APR_BPS, DAY_IN_ROUNDS, ROUNDS_PER_YEAR,
        )

        amount = 50_000
        for tier in range(4):
            expected = (amount * TIER_APR_BPS[tier] * DAY_IN_ROUNDS) // (
                10_000 * ROUNDS_PER_YEAR
            )
            actual = calculate_interest(amount, tier)
            self.assertEqual(actual, expected, f"Mismatch at tier {tier}")
            self.assertIsInstance(actual, int)
            self.assertGreaterEqual(actual, 0)

        print("\n📐  TEST 5 PASSED — Interest formula matches AVM")


# ──────────────────────────────────────────────────────────────────────────────
# Test 6 — Anthropic provider path
# ──────────────────────────────────────────────────────────────────────────────

class TestAnthropicProviderPath(unittest.TestCase):
    """Test case 6: ORACLE_PROVIDER=anthropic uses _anthropic_client, not _openai_client."""

    def setUp(self) -> None:
        os.environ["ORACLE_PROVIDER"] = "anthropic"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"
        self.mock_algod = _make_mock_algod()

    def tearDown(self) -> None:
        os.environ["ORACLE_PROVIDER"] = "venice"

    def test_anthropic_path_approved(self) -> None:
        """When ORACLE_PROVIDER=anthropic, beta.messages.parse is called."""
        mock_anthropic_response = MagicMock()
        mock_anthropic_response.parsed_output = CriteriaEvaluation(
            criterion_1_passed=True,
            criterion_2_passed=True,
            criterion_3_passed=True,
            criterion_4_passed=True,
            overall_approved=True,
            task_risk_level="low",
            denial_reason="",
            risk_summary="Test approval via Anthropic path.",
        )

        with patch("bloopa_sdk.oracle.Anthropic") as mock_anthropic_class:
            mock_ant_instance = MagicMock()
            mock_anthropic_class.return_value = mock_ant_instance
            mock_ant_instance.beta.messages.parse.return_value = mock_anthropic_response

            oracle = RiskOracle(
                algod_client=self.mock_algod,
                anthropic_api_key="sk-ant-test-key",
                demo_mode=True,
            )

            self.assertEqual(oracle.provider, "anthropic")
            self.assertIsNone(oracle._openai_client)
            self.assertIsNotNone(oracle._anthropic_client)

            decision = oracle.evaluate(
                agent_address=FAKE_SENDER,
                amount_microalgo=50_000,
                payment_count=21,
                outstanding_microalgo=0,
                task_description="Fetch ETH price from CoinGecko",
                expected_return_microalgo=80_000,
                estimated_task_rounds=120,
            )

        self.assertIsInstance(decision, RiskDecision)
        self.assertTrue(decision.approved)
        self.assertEqual(decision.attestation_hash, FAKE_HASH)
        mock_ant_instance.beta.messages.parse.assert_called_once()

        print("\n🤖  TEST 6 PASSED — Anthropic provider path used correctly")
        print(f"    Model: {oracle.model}")
        print(f"    Provider: {oracle.provider}")


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  BLOOPA SDK — RISK ORACLE OFFLINE TESTS")
    print("=" * 60)
    print("  No real API key or algod connection required.")
    print("  All external calls are mocked.")
    print()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestRiskOraclePass))
    suite.addTests(loader.loadTestsFromTestCase(TestRiskOracleFailCriterion3))
    suite.addTests(loader.loadTestsFromTestCase(TestTierCapPreGate))
    suite.addTests(loader.loadTestsFromTestCase(TestRiskOracleFailCriterion4))
    suite.addTests(loader.loadTestsFromTestCase(TestInterestFormula))
    suite.addTests(loader.loadTestsFromTestCase(TestAnthropicProviderPath))

    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    print()
    if result.wasSuccessful():
        print("=" * 60)
        print("  ALL TESTS PASSED [OK]")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("  SOME TESTS FAILED [FAIL]")
        print("=" * 60)
        sys.exit(1)
