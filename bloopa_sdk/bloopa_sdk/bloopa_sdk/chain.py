"""
chain.py — All algosdk interactions for the Bloopa credit protocol.

No Claude calls. No criteria logic. Pure on-chain mechanics only.
"""

from algosdk import account, mnemonic, transaction, logic, encoding
from algosdk.abi import Method
from algosdk.v2client import algod
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    AccountTransactionSigner,
    TransactionWithSigner,
)

# ── Testnet defaults ───────────────────────────────────────────────────────────
ALGOD_TESTNET_URL: str = "https://testnet-api.algonode.cloud"
ALGOD_TESTNET_TOKEN: str = ""

# ── ABI method objects ─────────────────────────────────────────────────────────
# Defined at module level so they are parsed once and reused.

METHOD_REGISTER = Method.from_signature("register(pay)void")

METHOD_RECORD_PAYMENT = Method.from_signature("record_payment(uint64)uint64")

METHOD_DRAW = Method.from_signature("draw(uint64,byte[32])void")

METHOD_REPAY = Method.from_signature("repay(pay)void")

METHOD_GET_POSITION = Method.from_signature(
    "get_position(address)"
    "(uint64,uint64,uint64,uint64,uint64,uint64,uint64,uint64,uint64)"
)


# ── Client helpers ─────────────────────────────────────────────────────────────

def make_algod_client(url: str = ALGOD_TESTNET_URL) -> algod.AlgodClient:
    """Create an AlgodClient connected to the given node URL.

    Args:
        url: Algod REST endpoint.  Defaults to the Algonode testnet gateway.

    Returns:
        Initialised :class:`algosdk.v2client.algod.AlgodClient`.
    """
    return algod.AlgodClient(ALGOD_TESTNET_TOKEN, url)


# ── Key / address utilities ───────────────────────────────────────────────────

def address_from_mnemonic(mnemonic_phrase: str) -> str:
    """Derive the Algorand address from a 25-word mnemonic.

    Args:
        mnemonic_phrase: Space-separated 25-word Algorand mnemonic.

    Returns:
        Base32 Algorand address string.
    """
    private_key = mnemonic.to_private_key(mnemonic_phrase)
    return account.address_from_private_key(private_key)


def private_key_from_mnemonic(mnemonic_phrase: str) -> str:
    """Derive the private key from a 25-word mnemonic.

    Args:
        mnemonic_phrase: Space-separated 25-word Algorand mnemonic.

    Returns:
        Base64-encoded private key string suitable for algosdk signers.
    """
    return mnemonic.to_private_key(mnemonic_phrase)


def get_app_address(app_id: int) -> str:
    """Return the escrow address of an Algorand application.

    Args:
        app_id: The numeric application ID.

    Returns:
        Base32 Algorand address of the application.
    """
    return logic.get_application_address(app_id)


# ── On-chain read ──────────────────────────────────────────────────────────────

def get_position(
    algod_client: algod.AlgodClient,
    app_id: int,
    agent_address: str,
    signer: AccountTransactionSigner,
) -> dict:
    """Read an agent's on-chain credit position via ``get_position(address)``.

    Uses ``atc.simulate()`` (not ``execute()``) so no transaction is submitted
    and no fees are paid.  The call returns instantly without waiting for block
    confirmation.

    Args:
        algod_client: Connected AlgodClient.
        app_id: Bloopa contract application ID.
        agent_address: Algorand address to query.
        signer: AccountTransactionSigner for the agent wallet (required by ATC
            even for simulated calls).

    Returns:
        Dict with keys:
            ``stake_amount``, ``payment_count``, ``tier_max_draw``,
            ``outstanding``, ``is_defaulted``, ``tier``, ``apr_bps``,
            ``daily_drawn``, ``repay_by_round`` -- all ``int``.
    """
    sp = algod_client.suggested_params()
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=app_id,
        method=METHOD_GET_POSITION,
        sender=agent_address,
        sp=sp,
        signer=signer,
        method_args=[agent_address],
    )
    # simulate() is a read-only dry-run -- no transaction is broadcast.
    # The response object has the same .abi_results interface as execute().
    sim_result = atc.simulate(algod_client)
    values = sim_result.abi_results[0].return_value  # list of 9 ints

    return {
        "stake_amount":   int(values[0]),
        "payment_count":  int(values[1]),
        "tier_max_draw":  int(values[2]),
        "outstanding":    int(values[3]),
        "is_defaulted":   int(values[4]),
        "tier":           int(values[5]),
        "apr_bps":        int(values[6]),
        "daily_drawn":    int(values[7]),
        "repay_by_round": int(values[8]),
    }


# ── On-chain writes ────────────────────────────────────────────────────────────

def do_draw(
    algod_client: algod.AlgodClient,
    app_id: int,
    agent_address: str,
    private_key: str,
    amount_microalgo: int,
    attestation_hash: bytes,
) -> str:
    """Call ``draw(uint64, byte[32])`` on the Bloopa contract.

    The ``attestation_hash`` must be exactly 32 bytes.  The algosdk ATC
    encodes Python ``bytes`` as ABI ``byte[32]`` automatically.

    In demo mode pass ``bytes(32)`` (32 zero bytes); the contract skips
    verification when ``skip_attestation == 1``.

    Args:
        algod_client: Connected AlgodClient.
        app_id: Bloopa contract application ID.
        agent_address: Sending agent's Algorand address.
        private_key: Agent's private key (from :func:`private_key_from_mnemonic`).
        amount_microalgo: Draw amount in microALGO.
        attestation_hash: Exactly 32 bytes.  Use :func:`~bloopa_sdk.hash_util.demo_hash`
            in demo mode or :func:`~bloopa_sdk.hash_util.compute_attestation_hash`
            in production.

    Returns:
        Confirmed transaction ID string.
    """
    assert len(attestation_hash) == 32, (
        f"attestation_hash must be exactly 32 bytes, got {len(attestation_hash)}"
    )

    sp = algod_client.suggested_params()
    signer = AccountTransactionSigner(private_key)
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=app_id,
        method=METHOD_DRAW,
        sender=agent_address,
        sp=sp,
        signer=signer,
        method_args=[amount_microalgo, attestation_hash],
    )
    result = atc.execute(algod_client, 4)
    return result.tx_ids[0]


def do_repay(
    algod_client: algod.AlgodClient,
    app_id: int,
    agent_address: str,
    private_key: str,
    amount_microalgo: int,
) -> str:
    """Call ``repay(pay)`` on the Bloopa contract.

    The ``repay`` method takes a payment transaction as its ABI argument.
    The PaymentTxn sends ``amount_microalgo`` directly to the contract's
    escrow address.

    Args:
        algod_client: Connected AlgodClient.
        app_id: Bloopa contract application ID.
        agent_address: Repaying agent's Algorand address.
        private_key: Agent's private key.
        amount_microalgo: Amount to repay in microALGO (should equal
            ``total_repayable`` from the last draw).

    Returns:
        Confirmed transaction ID string.
    """
    sp = algod_client.suggested_params()
    signer = AccountTransactionSigner(private_key)
    app_address = logic.get_application_address(app_id)

    pay_txn = transaction.PaymentTxn(
        sender=agent_address,
        sp=sp,
        receiver=app_address,
        amt=amount_microalgo,
    )
    pay_tws = TransactionWithSigner(pay_txn, signer)

    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=app_id,
        method=METHOD_REPAY,
        sender=agent_address,
        sp=sp,
        signer=signer,
        method_args=[pay_tws],
    )
    result = atc.execute(algod_client, 4)
    return result.tx_ids[0]


def do_record_payment(
    algod_client: algod.AlgodClient,
    app_id: int,
    agent_address: str,
    private_key: str,
    amount_microalgo: int = 1000,
) -> int:
    """Call ``record_payment(uint64)`` on the Bloopa contract.

    Records an off-chain payment to increment the agent's payment count
    and potentially upgrade their tier.

    Args:
        algod_client: Connected AlgodClient.
        app_id: Bloopa contract application ID.
        agent_address: Agent's Algorand address.
        private_key: Agent's private key.
        amount_microalgo: Payment amount to record in microALGO.
            Defaults to 1000 (1 milliALGO, the minimum meaningful value).

    Returns:
        New tier number (0–3) returned by the contract.
    """
    sp = algod_client.suggested_params()
    signer = AccountTransactionSigner(private_key)
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=app_id,
        method=METHOD_RECORD_PAYMENT,
        sender=agent_address,
        sp=sp,
        signer=signer,
        method_args=[amount_microalgo],
    )
    result = atc.execute(algod_client, 4)
    return int(result.abi_results[0].return_value)


def do_register(
    algod_client: algod.AlgodClient,
    app_id: int,
    agent_address: str,
    private_key: str,
    stake_microalgo: int = 1_000_000,
) -> str:
    """Call ``register(pay)`` on the Bloopa contract.

    Registers the agent and stakes ALGO to establish a credit line.

    Args:
        algod_client: Connected AlgodClient.
        app_id: Bloopa contract application ID.
        agent_address: Agent's Algorand address.
        private_key: Agent's private key.
        stake_microalgo: Stake amount in microALGO.  Defaults to 1 ALGO.

    Returns:
        Confirmed transaction ID string.
    """
    sp = algod_client.suggested_params()
    signer = AccountTransactionSigner(private_key)
    app_address = logic.get_application_address(app_id)

    pay_txn = transaction.PaymentTxn(
        sender=agent_address,
        sp=sp,
        receiver=app_address,
        amt=stake_microalgo,
    )
    pay_tws = TransactionWithSigner(pay_txn, signer)

    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=app_id,
        method=METHOD_REGISTER,
        sender=agent_address,
        sp=sp,
        signer=signer,
        method_args=[pay_tws],
    )
    result = atc.execute(algod_client, 4)
    return result.tx_ids[0]
