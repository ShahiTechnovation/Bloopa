/**
 * contract.js — Single source of truth for Bloopa contract config.
 *
 * APP_ID and APP_ADDRESS come from the deployed testnet contract.
 * ABI_METHODS mirror contract.py / bloopa_usdc.py method signatures exactly.
 */

export const APP_ID = 764373926;

export const APP_ADDRESS =
  "KQAQFT7XLZ5GITHZOCKYXFNPRRVX3XZGTRYOPFFD5KGFPGGTI6UATQ7V3U";

export const USDC_APP_ID = 764377779;

export const USDC_APP_ADDRESS =
  "3EA5UXVWHDJWXUAFHJPAGP2W7P44VXINRSIUE65ESN66BF5EPZNEX7KI5Q";

export const TESTNET_ALGOD    = "https://testnet-api.algonode.cloud";
export const TESTNET_INDEXER  = "https://testnet-idx.algonode.cloud";

// Default currency — USDC is the platform's primary currency
export const DEFAULT_CURRENCY = "USDC";

export const MIN_STAKE_MICROALGO = 1_000_000; // 1 ALGO

// ABI method signatures — must match contract.py exactly
export const ABI_METHODS = {
  register: {
    name: "register",
    args: [{ type: "pay", name: "pay" }],
    returns: { type: "void" },
  },
  record_payment: {
    name: "record_payment",
    args: [{ type: "uint64", name: "amount" }],
    returns: { type: "uint64" },
  },
  draw: {
    name: "draw",
    args: [
      { type: "uint64", name: "amount" },
      { type: "byte[32]", name: "attestation_hash" },
    ],
    returns: { type: "void" },
  },
  repay: {
    name: "repay",
    args: [{ type: "pay", name: "pay" }],
    returns: { type: "void" },
  },
  slash: {
    name: "slash",
    args: [{ type: "address", name: "agent" }],
    returns: { type: "void" },
  },
  get_position: {
    name: "get_position",
    args: [{ type: "address", name: "agent" }],
    returns: {
      type: "(uint64,uint64,uint64,uint64,uint64,uint64,uint64,uint64,uint64)",
    },
  },

  // ─── USDC contract methods ────────────────────────────────────────────────
  draw_usdc: {
    name: "draw_usdc",
    args: [
      { type: "uint64", name: "amount" },
      { type: "byte[32]", name: "attestation_hash" },
    ],
    returns: { type: "void" },
  },
  draw_and_pay: {
    name: "draw_and_pay",
    args: [
      { type: "uint64", name: "amount" },
      { type: "address", name: "payee" },
      { type: "byte[32]", name: "attestation_hash" },
    ],
    returns: { type: "void" },
  },
  repay_usdc: {
    name: "repay_usdc",
    args: [{ type: "axfer", name: "axfer" }],
    returns: { type: "void" },
  },
  get_usdc_position: {
    name: "get_usdc_position",
    args: [{ type: "address", name: "agent" }],
    returns: { type: "(uint64,uint64,uint64,uint64)" },
  },
  configure_usdc: {
    name: "configure_usdc",
    args: [{ type: "asset", name: "usdc_asset" }],
    returns: { type: "void" },
  },
  // seed_usdc_treasury — now open to ALL callers (not creator-only).
  // This enables the atomic Tinyman-swap + seed + draw flow.
  seed_usdc_treasury: {
    name: "seed_treasury",
    args: [{ type: "axfer", name: "axfer" }],
    returns: { type: "void" },
  },
};

// USDC ASA IDs
export const USDC_ASA_ID_TESTNET = 10_458_941;
export const USDC_ASA_ID_MAINNET = 31_566_704;
export const USDC_ASA_ID = USDC_ASA_ID_TESTNET;  // switch for mainnet

// ──────────────────────────────────────────────────────────────────────────────
// Tier constants — must match contract.py / bloopa_usdc.py exactly
// ──────────────────────────────────────────────────────────────────────────────

export const TIER_THRESHOLDS = [0, 10, 50, 100]; // payment_count thresholds

// Per-draw hard caps (microALGO / micro-USDC)
export const TIER_PER_DRAW_CAPS = [
  100_000n,    // T0: $0.10
  500_000n,    // T1: $0.50
  2_000_000n,  // T2: $2.00
  5_000_000n,  // T3: $5.00
];

// Daily aggregate caps (microALGO / micro-USDC)
export const TIER_DAILY_CAPS = [
  500_000n,     // T0: $0.50
  2_000_000n,   // T1: $2.00
  10_000_000n,  // T2: $10.00
  25_000_000n,  // T3: $25.00
];

// APR in basis points (lower tier → higher APR)
export const TIER_APR_BPS = [2400n, 1600n, 900n, 400n];

/**
 * Derive tier data from payment_count — mirrors on-chain _get_tier exactly.
 * @param {BigInt|number} paymentCount
 * @returns {{ tier: bigint, perDrawCap: bigint, dailyCap: bigint, aprBps: bigint }}
 */
export function getTierData(paymentCount) {
  const pc = BigInt(paymentCount);
  let tier;
  if (pc >= 100n)     tier = 3;
  else if (pc >= 50n) tier = 2;
  else if (pc >= 10n) tier = 1;
  else                tier = 0;

  return {
    tier:       BigInt(tier),
    perDrawCap: TIER_PER_DRAW_CAPS[tier],
    dailyCap:   TIER_DAILY_CAPS[tier],
    aprBps:     TIER_APR_BPS[tier],
  };
}

// Minimum practical amounts
export const MIN_DRAW_MICROALGO = 1_000n;    // 0.001 ALGO
export const MIN_DRAW_MICRO_USDC = 10_000n;  // 0.01 USDC
export const MIN_REPAY_MICROALGO = 1_000n;
export const MIN_REPAY_MICRO_USDC = 10_000n;

// ──────────────────────────────────────────────────────────────────────────────

// USDC has 6 decimal places — same as microALGO
export const toMicroUsdc = (usdc) => Math.round(usdc * 1_000_000);
export const fromMicroUsdc = (micro) => micro / 1_000_000;

// Helper: microALGO -> ALGO display string
export const toAlgo = (microAlgo) =>
  (Number(microAlgo) / 1_000_000).toFixed(6);

// Helper: ALGO input string -> microALGO as BigInt
export const toMicroAlgo = (algo) =>
  BigInt(Math.round(parseFloat(algo) * 1_000_000));

// x402 GoPlausible facilitator (Algorand testnet)
export const X402_FACILITATOR_URL = "https://x402.goplausible.xyz";
// Demo protected resource endpoint (GoPlausible testnet demo)
export const X402_DEMO_RESOURCE_URL = "https://x402.goplausible.xyz/demo/resource";
