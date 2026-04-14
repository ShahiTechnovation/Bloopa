/**
 * Dashboard.jsx — Hero position screen.
 *
 * Hyperliquid-inspired data-dense position overview + 4 action panels:
 *   A. Record Payment (top-left)
 *   B. Draw Credit (top-right)
 *   C. Repay Outstanding (bottom-left, full width)
 *   D. Slash Agent (bottom-right, danger zone)
 */

import React, { useState, useEffect, useRef } from "react";
import { useWallet } from "../context/WalletContext.jsx";
import { useContract } from "../context/ContractContext.jsx";
import { useToast } from "./ui/Toast.jsx";
import Button from "./ui/Button.jsx";
import Input from "./ui/Input.jsx";
import { fmtAlgo, fmtAddress } from "../utils/format.js";
import { SkeletonStatCard } from "./ui/Skeleton.jsx";

/* ── Utilisation Bar ── */
function UtilisationBar({ percent }) {
  const barColor =
    percent > 80 ? "var(--danger)"
    : percent > 60 ? "var(--warning)"
    : "var(--success)";

  return (
    <div className="flex items-center gap-3">
      <div
        className="flex-1 h-1.5 rounded-full overflow-hidden"
        style={{ background: "var(--bg-elevated)" }}
      >
        <div
          className="h-full rounded-full animate-grow"
          style={{
            width: `${Math.min(percent, 100)}%`,
            background: barColor,
            transition: "background-color 0.3s ease",
          }}
        />
      </div>
      <span
        className="num text-xs font-semibold shrink-0"
        style={{ color: barColor }}
      >
        {percent}% used
      </span>
    </div>
  );
}

/* ── Position Overview Card ── */
function PositionCard({ position, isLoading }) {
  const stake = fmtAlgo(position.stake);
  const creditLimit = fmtAlgo(position.creditLimit);
  const outstanding = fmtAlgo(position.outstanding);
  const available = fmtAlgo(position.creditLimit - position.outstanding);
  const utilization =
    position.creditLimit > 0n
      ? Number((position.outstanding * 100n) / position.creditLimit)
      : 0;

  const prevLimitRef = useRef(creditLimit);
  const prevOutRef = useRef(outstanding);
  const [limitFlash, setLimitFlash] = useState("");
  const [outFlash, setOutFlash] = useState("");

  useEffect(() => {
    if (prevLimitRef.current !== creditLimit) {
      setLimitFlash("flash-success");
      setTimeout(() => setLimitFlash(""), 1500);
      prevLimitRef.current = creditLimit;
    }
  }, [creditLimit]);

  useEffect(() => {
    if (prevOutRef.current !== outstanding) {
      setOutFlash(position.outstanding > 0n ? "flash-danger" : "flash-success");
      setTimeout(() => setOutFlash(""), 1500);
      prevOutRef.current = outstanding;
    }
  }, [outstanding, position.outstanding]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <SkeletonStatCard key={i} />)}
      </div>
    );
  }

  return (
    <div
      className="card p-6 transition-all duration-300"
      style={{
        borderColor: position.isDefaulted ? "var(--danger)" : undefined,
        boxShadow: position.isDefaulted
          ? "0 0 0 1px var(--danger), 0 4px 24px rgba(0,0,0,0.4), 0 0 20px rgba(239,68,68,0.1)"
          : undefined,
      }}
    >
      {/* Header row */}
      <div className="flex items-center justify-between mb-6">
        <span
          className="text-[11px] font-sans font-medium uppercase tracking-[0.1em]"
          style={{ color: "var(--text-secondary)" }}
        >
          Agent Position
        </span>
        <div className="flex items-center gap-2">
          <span
            className="w-2 h-2 rounded-full"
            style={{
              background: position.isDefaulted ? "var(--danger)" : "var(--success)",
            }}
          />
          <span
            className="text-xs font-sans font-semibold uppercase"
            style={{
              color: position.isDefaulted ? "var(--danger)" : "var(--success)",
            }}
          >
            {position.isDefaulted ? "DEFAULTED" : "ACTIVE"}
          </span>
        </div>
      </div>

      {/* Main metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-6">
        <div>
          <p className="text-[11px] font-sans font-medium uppercase tracking-[0.1em] mb-1" style={{ color: "var(--text-secondary)" }}>
            Credit Limit
          </p>
          <p className={`num text-[28px] font-semibold text-[var(--text-primary)] leading-tight ${limitFlash}`}>
            {creditLimit}
          </p>
          <p className="text-[11px] font-mono uppercase" style={{ color: "var(--text-muted)" }}>ALGO</p>
        </div>
        <div>
          <p className="text-[11px] font-sans font-medium uppercase tracking-[0.1em] mb-1" style={{ color: "var(--text-secondary)" }}>
            Outstanding
          </p>
          <p className={`num text-[28px] font-semibold text-[var(--text-primary)] leading-tight ${outFlash}`}>
            {outstanding}
          </p>
          <p className="text-[11px] font-mono uppercase" style={{ color: "var(--text-muted)" }}>ALGO</p>
        </div>
        <div>
          <p className="text-[11px] font-sans font-medium uppercase tracking-[0.1em] mb-1" style={{ color: "var(--text-secondary)" }}>
            Available
          </p>
          <p className="num text-[28px] font-semibold leading-tight" style={{ color: "var(--success)" }}>
            {available}
          </p>
          <p className="text-[11px] font-mono uppercase" style={{ color: "var(--text-muted)" }}>ALGO</p>
        </div>
      </div>

      {/* Utilisation bar */}
      <UtilisationBar percent={utilization} />

      {/* Secondary metrics */}
      <div className="grid grid-cols-2 gap-4 mt-6 pt-6" style={{ borderTop: "1px solid var(--bg-border)" }}>
        <div>
          <p className="text-[11px] font-sans font-medium uppercase tracking-[0.1em] mb-1" style={{ color: "var(--text-secondary)" }}>
            Stake Locked
          </p>
          <p className="num text-lg font-semibold text-[var(--text-primary)]">
            {stake} <span className="text-xs" style={{ color: "var(--text-muted)" }}>ALGO</span>
          </p>
        </div>
        <div>
          <p className="text-[11px] font-sans font-medium uppercase tracking-[0.1em] mb-1" style={{ color: "var(--text-secondary)" }}>
            Payments Made
          </p>
          <p className="num text-lg font-semibold text-[var(--text-primary)]">
            {position.paymentCount.toString()} <span className="text-xs" style={{ color: "var(--text-muted)" }}>payments</span>
          </p>
        </div>
      </div>
    </div>
  );
}

/* ── Panel wrapper ── */
function PanelHeader({ title }) {
  return (
    <p
      className="text-[11px] font-sans font-medium uppercase tracking-[0.1em] mb-4"
      style={{ color: "var(--text-secondary)" }}
    >
      {title}
    </p>
  );
}

export default function Dashboard() {
  const { address } = useWallet();
  const { position, loading, callRecordPayment, callDraw, callRepay, callSlash } = useContract();
  const { addToast } = useToast();

  const [recordInput, setRecordInput] = useState("");
  const [drawInput, setDrawInput] = useState("");
  const [repayInput, setRepayInput] = useState("");
  const [slashInput, setSlashInput] = useState("");

  const [activeAction, setActiveAction] = useState(null);

  // Computed values
  const available = Number(position.creditLimit - position.outstanding) / 1e6;
  const outstandingNum = Number(position.outstanding) / 1e6;

  // --- Action Handlers ---
  const handleRecord = async () => {
    const amt = parseFloat(recordInput);
    if (!amt || amt <= 0) return;
    setActiveAction("record");
    try {
      const newLimit = await callRecordPayment(recordInput);
      addToast(`↑ Credit limit increased to ${fmtAlgo(newLimit)} ALGO`, "success");
      setRecordInput("");
    } catch (err) {
      const msg = err.message?.includes("rejected") ? "Transaction rejected"
        : err.message?.includes("balance") ? "Insufficient balance"
        : err.message || "Record failed";
      addToast(msg, "error");
    }
    setActiveAction(null);
  };

  const handleDraw = async () => {
    const amt = parseFloat(drawInput);
    if (!amt || amt <= 0) return;
    setActiveAction("draw");
    try {
      await callDraw(drawInput);
      addToast(`→ ${parseFloat(drawInput).toFixed(6)} ALGO sent to wallet`, "success");
      setDrawInput("");
    } catch (err) {
      const msg = err.message?.includes("rejected") ? "Transaction rejected"
        : err.message?.includes("exceeds") ? "Amount exceeds available credit"
        : err.message || "Draw failed";
      addToast(msg, "error");
    }
    setActiveAction(null);
  };

  const handleRepay = async () => {
    const amt = parseFloat(repayInput);
    if (!amt || amt <= 0) return;
    setActiveAction("repay");
    try {
      await callRepay(repayInput);
      addToast(`← Repaid ${parseFloat(repayInput).toFixed(6)} ALGO`, "success");
      setRepayInput("");
    } catch (err) {
      const msg = err.message?.includes("rejected") ? "Transaction rejected"
        : err.message?.includes("balance") ? "Insufficient balance"
        : err.message || "Repayment failed";
      addToast(msg, "error");
    }
    setActiveAction(null);
  };

  const handleSlash = async () => {
    if (!slashInput || slashInput.length < 58) return;
    setActiveAction("slash");
    try {
      await callSlash(slashInput);
      addToast(`Agent ${fmtAddress(slashInput)} slashed. Stake burned.`, "error", 5000);
      setSlashInput("");
    } catch (err) {
      const msg = err.message?.includes("rejected") ? "Transaction rejected"
        : err.message || "Slash failed";
      addToast(msg, "error");
    }
    setActiveAction(null);
  };

  // Pre-computed previews
  const recordAmt = parseFloat(recordInput) || 0;
  const currentLimitAlgo = Number(position.creditLimit) / 1e6;
  const afterPaymentLimit = currentLimitAlgo + (recordAmt > 0 ? 0.5 : 0); // approx +0.5 per payment

  const repayAmt = parseFloat(repayInput) || 0;
  const outAfterRepay = Math.max(0, outstandingNum - repayAmt);

  const isSelfSlash = slashInput === address;

  return (
    <div className="flex flex-col gap-6">
      {/* Position overview */}
      <PositionCard position={position} isLoading={loading && position.stake === 0n} />

      {/* Action panels — 2×2 grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Panel A: Record Payment */}
        <div className="card p-6">
          <PanelHeader title="Record Payment" />

          <Input
            id="record-amount"
            type="number"
            suffix="ALGO"
            value={recordInput}
            onChange={(e) => setRecordInput(e.target.value)}
            placeholder="0.000000"
          />

          {/* Live preview */}
          {recordAmt > 0 && (
            <div className="mt-3 rounded-[8px] px-3 py-2.5 text-xs space-y-1" style={{ background: "var(--accent-dim)", border: "1px solid rgba(99,102,241,0.15)" }}>
              <div className="flex justify-between">
                <span className="font-sans text-[var(--text-secondary)]">Current limit</span>
                <span className="num text-[var(--text-primary)]">{currentLimitAlgo.toFixed(6)} ALGO</span>
              </div>
              <div className="flex justify-between">
                <span className="font-sans text-[var(--text-secondary)]">After payment</span>
                <span className="num" style={{ color: "var(--success)" }}>{afterPaymentLimit.toFixed(6)} ALGO</span>
              </div>
              <div className="flex justify-between">
                <span className="font-sans text-[var(--text-secondary)]">Δ change</span>
                <span className="num" style={{ color: "var(--accent)" }}>+0.500000 ALGO</span>
              </div>
            </div>
          )}

          <Button
            id="record-button"
            variant="primary"
            size="lg"
            className="w-full mt-4"
            onClick={handleRecord}
            loading={activeAction === "record"}
            disabled={!recordInput || parseFloat(recordInput) <= 0}
          >
            Record Payment
          </Button>
        </div>

        {/* Panel B: Draw Credit */}
        <div className="card p-6">
          <PanelHeader title="Draw Credit" />

          <p className="num text-xs mb-3" style={{ color: "var(--text-secondary)" }}>
            {available.toFixed(6)} ALGO available
          </p>

          <Input
            id="draw-amount"
            type="number"
            suffix="ALGO"
            value={drawInput}
            onChange={(e) => setDrawInput(e.target.value)}
            placeholder="0.000000"
          />

          {/* Quick draw buttons */}
          <div className="flex gap-2 mt-3">
            {[25, 50, "MAX"].map((pct) => {
              const val = pct === "MAX" ? available : available * (pct / 100);
              return (
                <button
                  key={pct}
                  onClick={() => setDrawInput(val.toFixed(6))}
                  className="flex-1 h-8 rounded-[6px] text-xs font-mono font-medium transition-all duration-150 hover:border-[var(--accent)] hover:text-[var(--accent)]"
                  style={{
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--bg-border)",
                    color: "var(--text-secondary)",
                  }}
                >
                  {pct === "MAX" ? "MAX" : `${pct}%`}
                </button>
              );
            })}
          </div>

          <Button
            id="draw-button"
            variant="primary"
            size="lg"
            className="w-full mt-4"
            onClick={handleDraw}
            loading={activeAction === "draw"}
            disabled={!drawInput || parseFloat(drawInput) <= 0}
          >
            Draw ALGO
          </Button>
        </div>

        {/* Panel C: Repay Outstanding */}
        <div className="card p-6">
          <PanelHeader title="Repay Outstanding" />

          {/* Repayment overview */}
          <div className="flex items-center justify-between text-xs mb-3">
            <span className="font-sans" style={{ color: "var(--text-secondary)" }}>Outstanding</span>
            <span className="num text-[var(--text-primary)]">{outstandingNum.toFixed(6)} ALGO</span>
          </div>

          <Input
            id="repay-amount"
            type="number"
            suffix="ALGO"
            value={repayInput}
            onChange={(e) => setRepayInput(e.target.value)}
            placeholder="0.000000"
          />

          {/* MAX button inline */}
          <button
            onClick={() => setRepayInput(outstandingNum.toFixed(6))}
            className="mt-2 text-[11px] font-mono px-2 py-1 rounded-[4px] transition-colors duration-150 hover:text-[var(--accent)]"
            style={{ color: "var(--text-muted)", background: "var(--bg-elevated)" }}
          >
            MAX
          </button>

          {/* Repayment progress preview */}
          {repayAmt > 0 && (
            <div className="mt-3 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-sans" style={{ color: "var(--text-secondary)" }}>After repay</span>
                <span className="num" style={{ color: "var(--success)" }}>{outAfterRepay.toFixed(6)} ALGO</span>
              </div>
              {/* Before bar */}
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-sans w-10" style={{ color: "var(--text-muted)" }}>Before</span>
                  <div className="flex-1 h-1 rounded-full" style={{ background: "var(--bg-elevated)" }}>
                    <div className="h-full rounded-full transition-all duration-300" style={{
                      width: `${position.creditLimit > 0n ? Number((position.outstanding * 100n) / position.creditLimit) : 0}%`,
                      background: "var(--warning)",
                    }} />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-sans w-10" style={{ color: "var(--text-muted)" }}>After</span>
                  <div className="flex-1 h-1 rounded-full" style={{ background: "var(--bg-elevated)" }}>
                    <div className="h-full rounded-full transition-all duration-300" style={{
                      width: `${position.creditLimit > 0n ? Math.max(0, Number(BigInt(Math.round(outAfterRepay * 1e6)) * 100n / position.creditLimit)) : 0}%`,
                      background: "var(--success)",
                    }} />
                  </div>
                </div>
              </div>
            </div>
          )}

          <Button
            id="repay-button"
            variant="primary"
            size="lg"
            className="w-full mt-4"
            onClick={handleRepay}
            loading={activeAction === "repay"}
            disabled={!repayInput || parseFloat(repayInput) <= 0}
          >
            Repay
          </Button>
        </div>

        {/* Panel D: Slash Agent (DANGER ZONE) */}
        <div
          className="card p-6"
          style={{ borderColor: "var(--danger)" }}
        >
          <div className="flex items-center justify-between mb-4">
            <span className="text-[11px] font-sans font-medium uppercase tracking-[0.1em]" style={{ color: "var(--danger)" }}>
              ⚠ Slash Agent
            </span>
            <div className="group relative">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" className="cursor-help">
                <circle cx="8" cy="8" r="6"/>
                <path d="M8 5.5v.01M8 7v3" strokeLinecap="round"/>
              </svg>
              {/* Tooltip */}
              <div className="absolute right-0 bottom-full mb-2 w-64 p-3 rounded-[8px] text-xs font-sans opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity duration-200 z-50"
                   style={{ background: "var(--bg-elevated)", border: "1px solid var(--bg-border)", color: "var(--text-secondary)", boxShadow: "0 4px 24px rgba(0,0,0,0.4)" }}>
                Slash delinquent agents with outstanding debt and no payments in 30+ rounds. Stake is burned to treasury.
              </div>
            </div>
          </div>

          <Input
            id="slash-address"
            type="text"
            value={slashInput}
            onChange={(e) => setSlashInput(e.target.value)}
            placeholder="ALGORAND ADDRESS..."
            inputClassName="text-sm"
            error={isSelfSlash ? "Cannot slash yourself" : ""}
          />

          <Button
            id="slash-button"
            variant="danger"
            size="lg"
            className="w-full mt-4"
            onClick={handleSlash}
            loading={activeAction === "slash"}
            disabled={!slashInput || slashInput.length < 58 || isSelfSlash}
          >
            Slash Agent
          </Button>
        </div>
      </div>
    </div>
  );
}
