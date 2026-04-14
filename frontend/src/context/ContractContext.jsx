/**
 * ContractContext.jsx — All 6 Bloopa contract method calls + position state.
 *
 * Exposes: {
 *   position, loading, error, activityLog, isOptedIn,
 *   fetchPosition, callRegister,
 *   callRecordPayment, callDraw,
 *   callRepay, callSlash
 * }
 *
 * Auto-refreshes position every 15 seconds when a wallet is connected.
 *
 * ── Key fixes (v2) ──
 * 1. Contract opt_in now initialises all local state keys → pc=262 resolved.
 * 2. fetchPosition / checkOptedIn use algodClient.accountApplicationInformation
 *    instead of raw fetch() — eliminates CORS and URL issues.
 * 3. sendRawTransaction response handled correctly for algosdk v3.
 * 4. makeSigner builds Pera/Defly-compatible signing payloads.
 * 5. ATC-based register and repay pass payment as TransactionWithSigner.
 */

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from "react";
import algosdk from "algosdk";
import { useWallet } from "./WalletContext.jsx";
import { algodClient } from "../utils/algod.js";
import {
  APP_ID,
  APP_ADDRESS,
  toMicroAlgo,
  ABI_METHODS,
} from "../utils/contract.js";

const ContractContext = createContext(null);

const DEFAULT_POSITION = {
  stake: 0n,
  paymentCount: 0n,
  creditLimit: 0n,
  outstanding: 0n,
  isDefaulted: false,
};

/**
 * Parse raw contract/network errors into human-readable messages.
 */
function parseError(err) {
  const msg = err?.message || String(err);
  if (
    msg.includes("rejected") ||
    msg.includes("CONNECT_MODAL_CLOSED") ||
    msg.includes("cancelled") ||
    msg.includes("Cancelled") ||
    msg.includes("Connection Cancelled")
  )
    return "Transaction rejected by user";
  if (msg.includes("overspend") || msg.includes("insufficient funds"))
    return "Insufficient ALGO balance";

  // ARC56 pc mapping (from Bloopa.arc56.json sourceInfo):
  //   pc=262 → "check self.stake_amount exists for account" (NOT opted in)
  //   pc=264 → "Agent already registered" (stake_amount > 0)
  if (msg.includes("pc=264") || msg.includes("Agent already registered"))
    return "You are already registered — try the Dashboard";
  if (
    msg.includes("pc=262") ||
    msg.includes("pc=261") ||
    msg.includes("cannot fetch key") ||
    msg.includes("has not opted in") ||
    msg.includes("check self.stake_amount exists")
  )
    return "Account not opted in — please try again";
  if (
    msg.includes("already registered")
  )
    return "Agent already registered";
  if (msg.includes("already opted in"))
    return "Already opted in — try registering";
  if (
    msg.includes("exceeds credit limit") ||
    msg.includes("Draw exceeds")
  )
    return "Amount exceeds available credit";
  if (
    msg.includes("not registered") ||
    msg.includes("Agent not registered")
  )
    return "Agent not registered";
  if (msg.includes("is defaulted") || msg.includes("Agent is defaulted"))
    return "Agent has been slashed";
  if (msg.includes("not delinquent"))
    return "Agent is not eligible for slashing";
  if (msg.includes("no outstanding"))
    return "Agent has no outstanding debt";
  if (
    (msg.includes("network") || msg.includes("fetch")) &&
    !msg.includes("cannot fetch key") &&
    !msg.includes("logic eval")
  )
    return "Network error — please retry";
  if (msg.includes("logic eval error")) {
    const match = msg.match(/logic eval error: (.+?)(?:\.|$)/);
    return match ? match[1] : "Transaction failed on-chain";
  }
  return msg.length > 120 ? msg.slice(0, 120) + "…" : msg;
}

export function ContractProvider({ children }) {
  const { address, activeWallet } = useWallet();
  const [position, setPosition] = useState(DEFAULT_POSITION);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activityLog, setActivityLog] = useState([]);
  const [isOptedIn, setIsOptedIn] = useState(false);
  const refreshRef = useRef(null);

  const addActivity = useCallback((type, amount = null) => {
    setActivityLog((prev) => [
      { type, amount, round: null, timestamp: Date.now() },
      ...prev.slice(0, 19),
    ]);
  }, []);

  // ──────────────────────────────────────────
  // Helper — read a uint64 from TealKeyValue array.
  // algosdk v3 accountApplicationInformation returns objects with
  // camelCase or hyphenated keys depending on the endpoint.
  // ──────────────────────────────────────────
  const readLocalUint = (kvs, keyName) => {
    if (!kvs || kvs.length === 0) return 0n;
    const entry = kvs.find((kv) => {
      try {
        let decodedKey;
        if (typeof kv.key === "string") {
          // REST API / v3: key is base64 encoded
          decodedKey = atob(kv.key);
        } else if (kv.key instanceof Uint8Array) {
          // Model object: key is Uint8Array
          decodedKey = new TextDecoder().decode(kv.key);
        } else {
          decodedKey = String(kv.key);
        }
        return decodedKey === keyName;
      } catch {
        return false;
      }
    });
    if (!entry) return 0n;
    const val = entry.value?.uint ?? entry.value?.Uint ?? 0;
    return BigInt(val);
  };

  // ──────────────────────────────────────────
  // fetchPosition — uses algodClient for reliability.
  // 404 / error = not opted in (perfectly normal for new agents).
  // ──────────────────────────────────────────
  const fetchPosition = useCallback(async (addr) => {
    if (!addr) return;
    try {
      const appInfo = await algodClient
        .accountApplicationInformation(addr, APP_ID)
        .do();

      // algosdk v3 returns the object directly; check for local state
      const appLocalState =
        appInfo["app-local-state"] ?? appInfo["appLocalState"] ?? null;

      if (!appLocalState) {
        setIsOptedIn(false);
        setPosition(DEFAULT_POSITION);
        return;
      }

      const kvs =
        appLocalState["key-value"] ??
        appLocalState["keyValue"] ??
        appLocalState.keyValue ??
        [];

      setIsOptedIn(true);
      setPosition({
        stake: readLocalUint(kvs, "stake_amount"),
        paymentCount: readLocalUint(kvs, "payment_count"),
        creditLimit: readLocalUint(kvs, "credit_limit"),
        outstanding: readLocalUint(kvs, "outstanding"),
        isDefaulted: readLocalUint(kvs, "is_defaulted") === 1n,
      });
      setError(null);
    } catch (err) {
      // 404 is expected for accounts that haven't opted in
      const msg = err?.message ?? String(err);
      if (
        msg.includes("404") ||
        msg.includes("not found") ||
        msg.includes("application does not exist")
      ) {
        setIsOptedIn(false);
        setPosition(DEFAULT_POSITION);
        return;
      }
      console.warn("fetchPosition:", msg);
      setIsOptedIn(false);
      setPosition(DEFAULT_POSITION);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ──────────────────────────────────────────
  // checkOptedIn — uses algodClient directly.
  // Returns true only if the account has app-local-state for APP_ID.
  // ──────────────────────────────────────────
  const checkOptedIn = useCallback(async (addr) => {
    if (!addr) return false;
    try {
      const appInfo = await algodClient
        .accountApplicationInformation(addr, APP_ID)
        .do();
      const hasLocalState = !!(
        appInfo["app-local-state"] ??
        appInfo["appLocalState"]
      );
      console.log(
        "checkOptedIn:",
        addr.slice(0, 8) + "...",
        "=>",
        hasLocalState,
      );
      return hasLocalState;
    } catch {
      // 404 = not opted in
      return false;
    }
  }, []);

  // ──────────────────────────────────────────
  // makeSigner — ATC-compatible TransactionSigner for Pera/Defly.
  //
  // ATC calls signer(txnGroup, indexesToSign):
  //   txnGroup: Transaction[]
  //   indexesToSign: number[]
  //
  // Pera/Defly signTransaction() expects:
  //   signTransaction([ [{ txn, signers }, ...] ])
  //   The outer array is for multiple txn groups.
  //   The inner array is the group (one entry per txn).
  //
  // Returns: Uint8Array[] aligned with txnGroup length.
  // ──────────────────────────────────────────
  const makeSigner = useCallback(() => {
    return async (txnGroup, indexesToSign) => {
      if (!activeWallet) throw new Error("No wallet connected");

      // Build the signing request format for Pera/Defly
      const txnsToSign = txnGroup.map((txn, idx) => ({
        txn,
        signers: indexesToSign.includes(idx) ? [address] : [],
      }));

      // signTransaction expects an array of groups: [[...group1]]
      const signedTxns = await activeWallet.signTransaction([txnsToSign]);

      // signedTxns is Uint8Array[] — already aligned with txnGroup
      return signedTxns;
    };
  }, [address, activeWallet]);

  // ──────────────────────────────────────────
  // callRegister — Two-step flow:
  //   Step 1 (if needed): Submit opt-in as a separate signed transaction.
  //   Step 2: ATC group with [payment, register] method call.
  //
  // The opt-in is separated from the ATC group because the contract's
  // register() method reads local state that must exist (set by opt-in).
  // ──────────────────────────────────────────
  const callRegister = useCallback(
    async (stakeAlgo) => {
      setLoading(true);
      setError(null);
      try {
        if (!activeWallet) throw new Error("No wallet connected");

        const signer = makeSigner();

        // ── Step 1: Opt-in (if not already opted in) ──
        const alreadyOptedIn = await checkOptedIn(address);
        console.log("callRegister: alreadyOptedIn =", alreadyOptedIn);

        if (!alreadyOptedIn) {
          console.log("callRegister: Submitting opt-in transaction...");
          const sp1 = await algodClient.getTransactionParams().do();
          const optInTxn = algosdk.makeApplicationOptInTxnFromObject({
            sender: address,
            appIndex: APP_ID,
            suggestedParams: { ...sp1, fee: 1000, flatFee: true },
          });

          // Sign via wallet
          const signedOptIn = await activeWallet.signTransaction([
            [{ txn: optInTxn, signers: [address] }],
          ]);

          // Submit — signedOptIn may be a single Uint8Array or array
          const rawToSend = Array.isArray(signedOptIn)
            ? signedOptIn.filter(Boolean)
            : [signedOptIn];
          await algodClient.sendRawTransaction(rawToSend).do();

          // Wait for confirmation using the txn ID
          const optInTxId = optInTxn.txID();
          console.log("callRegister: Opt-in submitted, txID:", optInTxId);
          await algosdk.waitForConfirmation(algodClient, optInTxId, 4);
          console.log("callRegister: Opt-in confirmed!");
        }

        // ── Step 2: Register via ATC (payment + register call) ──
        console.log("callRegister: Submitting register transaction...");
        const sp2 = await algodClient.getTransactionParams().do();
        const stakeAmt = toMicroAlgo(stakeAlgo);

        const atc = new algosdk.AtomicTransactionComposer();

        // Payment txn — TransactionWithSigner for the "pay" method arg
        const payTxn = algosdk.makePaymentTxnWithSuggestedParamsFromObject({
          sender: address,
          receiver: APP_ADDRESS,
          amount: stakeAmt,
          suggestedParams: { ...sp2, fee: 1000, flatFee: true },
        });
        const payTws = { txn: payTxn, signer };

        // App call — ATC places payment before this in the group
        atc.addMethodCall({
          appID: APP_ID,
          method: new algosdk.ABIMethod(ABI_METHODS.register),
          methodArgs: [payTws],
          sender: address,
          suggestedParams: { ...sp2, fee: 2000, flatFee: true },
          signer,
        });

        await atc.execute(algodClient, 4);
        console.log("callRegister: Register confirmed!");

        await fetchPosition(address);
        setIsOptedIn(true);
        addActivity("register", stakeAlgo);
      } catch (err) {
        console.error("callRegister error:", err);
        const msg = parseError(err);
        setError(msg);
        throw new Error(msg);
      } finally {
        setLoading(false);
      }
    },
    [address, activeWallet, makeSigner, fetchPosition, checkOptedIn, addActivity]
  );

  // ──────────────────────────────────────────
  // callRecordPayment
  // Contract: record_payment(amount: uint64) → uint64
  // ──────────────────────────────────────────
  const callRecordPayment = useCallback(
    async (amountAlgo) => {
      setLoading(true);
      setError(null);
      try {
        if (!activeWallet) throw new Error("No wallet connected");

        const atc = new algosdk.AtomicTransactionComposer();
        const sp = await algodClient.getTransactionParams().do();

        atc.addMethodCall({
          appID: APP_ID,
          method: new algosdk.ABIMethod(ABI_METHODS.record_payment),
          methodArgs: [toMicroAlgo(amountAlgo)],
          sender: address,
          suggestedParams: { ...sp, fee: 1000, flatFee: true },
          signer: makeSigner(),
        });

        const result = await atc.execute(algodClient, 4);
        // returnValue is ABI-decoded: BigInt (uint64)
        const newLimit = result.methodResults[0].returnValue;
        await fetchPosition(address);
        addActivity("payment", amountAlgo);
        return newLimit;
      } catch (err) {
        console.error("callRecordPayment error:", err);
        const msg = parseError(err);
        setError(msg);
        throw new Error(msg);
      } finally {
        setLoading(false);
      }
    },
    [address, activeWallet, makeSigner, fetchPosition, addActivity]
  );

  // ──────────────────────────────────────────
  // callDraw
  // Contract: draw(amount: uint64) → void
  // Uses inner txn to send ALGO to caller → fee must be 2000 (covers inner txn)
  // ──────────────────────────────────────────
  const callDraw = useCallback(
    async (amountAlgo) => {
      setLoading(true);
      setError(null);
      try {
        if (!activeWallet) throw new Error("No wallet connected");

        const atc = new algosdk.AtomicTransactionComposer();
        const sp = await algodClient.getTransactionParams().do();

        atc.addMethodCall({
          appID: APP_ID,
          method: new algosdk.ABIMethod(ABI_METHODS.draw),
          methodArgs: [toMicroAlgo(amountAlgo)],
          sender: address,
          suggestedParams: { ...sp, fee: 2000, flatFee: true },
          signer: makeSigner(),
        });

        await atc.execute(algodClient, 4);
        await fetchPosition(address);
        addActivity("draw", amountAlgo);
      } catch (err) {
        console.error("callDraw error:", err);
        const msg = parseError(err);
        setError(msg);
        throw new Error(msg);
      } finally {
        setLoading(false);
      }
    },
    [address, activeWallet, makeSigner, fetchPosition, addActivity]
  );

  // ──────────────────────────────────────────
  // callRepay
  // Contract: repay(pay: PaymentTransaction) → void
  // Same pattern as register: payment passed as TransactionWithSigner.
  // ──────────────────────────────────────────
  const callRepay = useCallback(
    async (amountAlgo) => {
      setLoading(true);
      setError(null);
      try {
        if (!activeWallet) throw new Error("No wallet connected");

        const atc = new algosdk.AtomicTransactionComposer();
        const sp = await algodClient.getTransactionParams().do();
        const signer = makeSigner();

        // Payment txn as TransactionWithSigner
        const payTxn = algosdk.makePaymentTxnWithSuggestedParamsFromObject({
          sender: address,
          receiver: APP_ADDRESS,
          amount: toMicroAlgo(amountAlgo),
          suggestedParams: { ...sp, fee: 1000, flatFee: true },
        });
        const payTws = { txn: payTxn, signer };

        atc.addMethodCall({
          appID: APP_ID,
          method: new algosdk.ABIMethod(ABI_METHODS.repay),
          methodArgs: [payTws],
          sender: address,
          suggestedParams: { ...sp, fee: 1000, flatFee: true },
          signer,
        });

        await atc.execute(algodClient, 4);
        await fetchPosition(address);
        addActivity("repay", amountAlgo);
      } catch (err) {
        console.error("callRepay error:", err);
        const msg = parseError(err);
        setError(msg);
        throw new Error(msg);
      } finally {
        setLoading(false);
      }
    },
    [address, activeWallet, makeSigner, fetchPosition, addActivity]
  );

  // ──────────────────────────────────────────
  // callSlash
  // Contract: slash(agent: address) → void
  // ──────────────────────────────────────────
  const callSlash = useCallback(
    async (agentAddress) => {
      setLoading(true);
      setError(null);
      try {
        if (!activeWallet) throw new Error("No wallet connected");

        const atc = new algosdk.AtomicTransactionComposer();
        const sp = await algodClient.getTransactionParams().do();

        atc.addMethodCall({
          appID: APP_ID,
          method: new algosdk.ABIMethod(ABI_METHODS.slash),
          methodArgs: [agentAddress],
          sender: address,
          suggestedParams: { ...sp, fee: 1000, flatFee: true },
          signer: makeSigner(),
        });

        await atc.execute(algodClient, 4);
        await fetchPosition(address);
        addActivity("slash");
      } catch (err) {
        console.error("callSlash error:", err);
        const msg = parseError(err);
        setError(msg);
        throw new Error(msg);
      } finally {
        setLoading(false);
      }
    },
    [address, activeWallet, makeSigner, fetchPosition, addActivity]
  );

  // ──────────────────────────────────────────
  // Auto-refresh position every 15 seconds
  // ──────────────────────────────────────────
  useEffect(() => {
    if (!address) {
      setPosition(DEFAULT_POSITION);
      setIsOptedIn(false);
      setError(null);
      clearInterval(refreshRef.current);
      return;
    }
    fetchPosition(address);
    refreshRef.current = setInterval(() => fetchPosition(address), 15_000);
    return () => clearInterval(refreshRef.current);
  }, [address, fetchPosition]);

  return (
    <ContractContext.Provider
      value={{
        position,
        loading,
        error,
        activityLog,
        isOptedIn,
        fetchPosition,
        callRegister,
        callRecordPayment,
        callDraw,
        callRepay,
        callSlash,
      }}
    >
      {children}
    </ContractContext.Provider>
  );
}

export function useContract() {
  const ctx = useContext(ContractContext);
  if (!ctx) {
    throw new Error("useContract must be used inside ContractProvider");
  }
  return ctx;
}
