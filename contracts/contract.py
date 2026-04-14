"""
Bloopa — On-chain reputation credit protocol for AI agents.

Agents stake ALGO, build repayment history, unlock undercollateralised
credit lines. Defaulters get slashed. No human in loop.

ARC-4 compliant. Algorand Python (Puya compiler).
"""

import algopy
from algopy import (
    Account,
    Global,
    GlobalState,
    LocalState,
    Txn,
    UInt64,
    arc4,
    gtxn,
    itxn,
    op,
)


# ──────────────────────────────────────────────
# Events (arc4.Struct subclasses)
# ──────────────────────────────────────────────


class AgentRegistered(arc4.Struct):
    agent: arc4.Address
    stake: arc4.UInt64


class PaymentRecorded(arc4.Struct):
    agent: arc4.Address
    amount: arc4.UInt64
    new_limit: arc4.UInt64


class CreditDrawn(arc4.Struct):
    agent: arc4.Address
    amount: arc4.UInt64
    outstanding: arc4.UInt64


class Repaid(arc4.Struct):
    agent: arc4.Address
    amount: arc4.UInt64
    outstanding: arc4.UInt64


class AgentSlashed(arc4.Struct):
    agent: arc4.Address
    stake_burned: arc4.UInt64


# ──────────────────────────────────────────────
# Contract
# ──────────────────────────────────────────────


class Bloopa(arc4.ARC4Contract):
    """
    On-chain reputation credit protocol for AI agents.

    Local state schema:  7 × uint64, 0 × bytes
    Global state schema: 2 × uint64, 0 × bytes
    """

    # ── Global State ──
    treasury_balance: GlobalState[UInt64]
    total_agents: GlobalState[UInt64]

    # ── Local State (per opted-in agent) ──
    stake_amount: LocalState[UInt64]
    payment_count: LocalState[UInt64]
    total_repaid: LocalState[UInt64]
    outstanding: LocalState[UInt64]
    credit_limit: LocalState[UInt64]
    is_defaulted: LocalState[UInt64]  # 1 = defaulted
    last_payment_round: LocalState[UInt64]

    def __init__(self) -> None:
        self.treasury_balance = GlobalState(UInt64(0))
        self.total_agents = GlobalState(UInt64(0))

        self.stake_amount = LocalState(UInt64)
        self.payment_count = LocalState(UInt64)
        self.total_repaid = LocalState(UInt64)
        self.outstanding = LocalState(UInt64)
        self.credit_limit = LocalState(UInt64)
        self.is_defaulted = LocalState(UInt64)
        self.last_payment_round = LocalState(UInt64)

    # ──────────────────────────────────────────
    # Bare method — Opt-In
    # ──────────────────────────────────────────

    @arc4.baremethod(allow_actions=["OptIn"])
    def opt_in(self) -> None:
        """Allow agents to opt in — initialise all local state keys to zero.

        This is critical: Puya compiles local-state reads as
        app_local_get_ex + assert, which will fail if the key has never
        been written.  Initialising here guarantees register() can read
        stake_amount (and the other keys) without assertion errors.
        """
        self.stake_amount[Txn.sender] = UInt64(0)
        self.payment_count[Txn.sender] = UInt64(0)
        self.total_repaid[Txn.sender] = UInt64(0)
        self.outstanding[Txn.sender] = UInt64(0)
        self.credit_limit[Txn.sender] = UInt64(0)
        self.is_defaulted[Txn.sender] = UInt64(0)
        self.last_payment_round[Txn.sender] = UInt64(0)

    # ──────────────────────────────────────────
    # ABI Method 1 — register
    # ──────────────────────────────────────────

    @arc4.abimethod
    def register(self, pay: gtxn.PaymentTransaction) -> None:
        """
        Register a new agent by staking ALGO.

        Requirements:
        - Payment must be to the application address.
        - Minimum stake is 1 ALGO (1_000_000 microALGO).
        - Agent must not already be registered.
        """
        # Guards
        assert (
            pay.receiver == Global.current_application_address
        ), "Payment must be to application address"
        assert pay.amount >= UInt64(1_000_000), "Minimum stake is 1 ALGO"

        # Prevent double-registration: stake_amount must be 0
        # (opt-in initialises local state slots to 0)
        assert (
            self.stake_amount[Txn.sender] == UInt64(0)
        ), "Agent already registered"

        # Initialise local state
        self.stake_amount[Txn.sender] = pay.amount
        self.payment_count[Txn.sender] = UInt64(0)
        self.total_repaid[Txn.sender] = UInt64(0)
        self.outstanding[Txn.sender] = UInt64(0)
        self.credit_limit[Txn.sender] = pay.amount * UInt64(2)
        self.is_defaulted[Txn.sender] = UInt64(0)
        self.last_payment_round[Txn.sender] = op.Global.round

        # Update global state
        self.treasury_balance.value += pay.amount
        self.total_agents.value += UInt64(1)

        # Emit event
        arc4.emit(
            AgentRegistered(
                agent=arc4.Address(Txn.sender),
                stake=arc4.UInt64(pay.amount),
            )
        )

    # ──────────────────────────────────────────
    # ABI Method 2 — record_payment
    # ──────────────────────────────────────────

    @arc4.abimethod
    def record_payment(self, amount: arc4.UInt64) -> arc4.UInt64:
        """
        Record an off-chain M2M payment. No actual ALGO transfer.
        Builds repayment history → increases credit limit.

        Returns: the agent's new credit limit.
        """
        # Guards
        assert (
            self.is_defaulted[Txn.sender] == UInt64(0)
        ), "Agent is defaulted"
        assert (
            self.stake_amount[Txn.sender] > UInt64(0)
        ), "Agent not registered"

        # Update state
        self.payment_count[Txn.sender] += UInt64(1)
        self.last_payment_round[Txn.sender] = op.Global.round

        # Recompute credit limit
        self._recompute_limit(Txn.sender)

        new_limit = self.credit_limit[Txn.sender]

        # Emit event
        arc4.emit(
            PaymentRecorded(
                agent=arc4.Address(Txn.sender),
                amount=amount,
                new_limit=arc4.UInt64(new_limit),
            )
        )

        return arc4.UInt64(new_limit)

    # ──────────────────────────────────────────
    # ABI Method 3 — draw
    # ──────────────────────────────────────────

    @arc4.abimethod
    def draw(self, amount: arc4.UInt64) -> None:
        """
        Draw undercollateralised credit from the protocol.
        Sends ALGO from the contract to the calling agent.
        """
        # Guards
        assert (
            self.is_defaulted[Txn.sender] == UInt64(0)
        ), "Agent is defaulted"
        assert (
            self.stake_amount[Txn.sender] > UInt64(0)
        ), "Agent not registered"

        draw_amt = amount.native

        assert (
            self.outstanding[Txn.sender] + draw_amt
            <= self.credit_limit[Txn.sender]
        ), "Draw exceeds credit limit"
        assert (
            Global.current_application_address.balance >= draw_amt
        ), "Insufficient contract balance"

        # Send ALGO via inner transaction (fee pooling)
        itxn.Payment(
            receiver=Txn.sender,
            amount=draw_amt,
            fee=Global.min_txn_fee,
        ).submit()

        # Update outstanding
        self.outstanding[Txn.sender] += draw_amt

        # Emit event
        arc4.emit(
            CreditDrawn(
                agent=arc4.Address(Txn.sender),
                amount=arc4.UInt64(draw_amt),
                outstanding=arc4.UInt64(self.outstanding[Txn.sender]),
            )
        )

    # ──────────────────────────────────────────
    # ABI Method 4 — repay
    # ──────────────────────────────────────────

    @arc4.abimethod
    def repay(self, pay: gtxn.PaymentTransaction) -> None:
        """
        Repay outstanding credit by sending ALGO back
        to the contract.
        """
        # Guards
        assert (
            pay.receiver == Global.current_application_address
        ), "Payment must be to application address"
        assert pay.amount > UInt64(0), "Repayment must be > 0"

        repay_amt = pay.amount

        # Reduce outstanding, floor at 0
        current_outstanding = self.outstanding[Txn.sender]
        if repay_amt >= current_outstanding:
            self.outstanding[Txn.sender] = UInt64(0)
        else:
            self.outstanding[Txn.sender] = current_outstanding - repay_amt

        # Update repaid total and treasury
        self.total_repaid[Txn.sender] += repay_amt
        self.treasury_balance.value += repay_amt
        self.last_payment_round[Txn.sender] = op.Global.round

        # Recompute credit limit
        self._recompute_limit(Txn.sender)

        # Emit event
        arc4.emit(
            Repaid(
                agent=arc4.Address(Txn.sender),
                amount=arc4.UInt64(repay_amt),
                outstanding=arc4.UInt64(self.outstanding[Txn.sender]),
            )
        )

    # ──────────────────────────────────────────
    # ABI Method 5 — slash
    # ──────────────────────────────────────────

    @arc4.abimethod
    def slash(self, agent: arc4.Address) -> None:
        """
        Slash a delinquent agent. Anyone may call this.

        Conditions:
        - Agent has outstanding > 0
        - Agent has never made a payment (payment_count == 0)
          OR last payment was > 30 rounds ago.
        """
        agent_addr = agent.native

        # Guards
        assert (
            self.outstanding[agent_addr] > UInt64(0)
        ), "Agent has no outstanding debt"

        payment_count = self.payment_count[agent_addr]
        rounds_since = op.Global.round - self.last_payment_round[agent_addr]

        assert (
            payment_count == UInt64(0) or rounds_since > UInt64(30)
        ), "Agent is not delinquent"

        # Capture stake before zeroing
        stake = self.stake_amount[agent_addr]

        # Slash
        self.is_defaulted[agent_addr] = UInt64(1)
        self.credit_limit[agent_addr] = UInt64(0)
        self.stake_amount[agent_addr] = UInt64(0)

        # Stake stays in contract — record in treasury
        self.treasury_balance.value += stake

        # Emit event
        arc4.emit(
            AgentSlashed(
                agent=arc4.Address(agent_addr),
                stake_burned=arc4.UInt64(stake),
            )
        )

    # ──────────────────────────────────────────
    # ABI Method 6 — get_position (readonly)
    # ──────────────────────────────────────────

    @arc4.abimethod(readonly=True)
    def get_position(
        self, agent: arc4.Address
    ) -> tuple[arc4.UInt64, arc4.UInt64, arc4.UInt64, arc4.UInt64, arc4.UInt64]:
        """
        Read an agent's full position.

        Returns:
            (stake_amount, payment_count, credit_limit,
             outstanding, is_defaulted)
        """
        addr = agent.native

        return (
            arc4.UInt64(self.stake_amount[addr]),
            arc4.UInt64(self.payment_count[addr]),
            arc4.UInt64(self.credit_limit[addr]),
            arc4.UInt64(self.outstanding[addr]),
            arc4.UInt64(self.is_defaulted[addr]),
        )

    # ──────────────────────────────────────────
    # Private — credit limit formula
    # ──────────────────────────────────────────

    @algopy.subroutine
    def _recompute_limit(self, sender: Account) -> None:
        """
        Credit limit formula:
            base           = stake × 2
            history_bonus  = payment_count × 500_000
            repaid_bonus   = total_repaid // 10
            raw            = base + history_bonus + repaid_bonus
            cap            = stake × 10
            credit_limit   = min(raw, cap)
        """
        stake = self.stake_amount[sender]
        count = self.payment_count[sender]
        repaid = self.total_repaid[sender]

        base = stake * UInt64(2)
        history_bonus = count * UInt64(500_000)
        repaid_bonus = repaid // UInt64(10)

        raw = base + history_bonus + repaid_bonus
        cap = stake * UInt64(10)

        if raw > cap:
            self.credit_limit[sender] = cap
        else:
            self.credit_limit[sender] = raw
