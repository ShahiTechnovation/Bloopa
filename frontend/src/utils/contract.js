/**
 * contract.js — Single source of truth for Bloopa contract config.
 *
 * APP_ID and APP_ADDRESS come from the deployed testnet contract.
 * ABI_METHODS mirror contract.py method signatures exactly.
 */

export const APP_ID = 762466410;

export const APP_ADDRESS =
  "Z2AJEBCQBWD5VOYVYIE3LUCCFVRY2H2ZMHAQEEG34ZKCNH7NACTXBGGGQY";

export const TESTNET_ALGOD = "https://testnet-api.algonode.cloud";

export const TESTNET_INDEXER = "https://testnet-idx.algonode.cloud";

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
};

// Helper: microALGO -> ALGO display string
export const toAlgo = (microAlgo) =>
  (Number(microAlgo) / 1_000_000).toFixed(6);

// Helper: ALGO input string -> microALGO as BigInt
export const toMicroAlgo = (algo) =>
  BigInt(Math.round(parseFloat(algo) * 1_000_000));
