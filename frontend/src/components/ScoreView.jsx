/**
 * ScoreView.jsx — Credit score visualization + multiplier ladder + activity log.
 *
 * Hero: SVG arc gauge with animated score
 * Below: Stats row, credit multiplier ladder, recent activity log
 */

import React, { useState, useMemo, useEffect, useRef } from "react";
import { useContract } from "../context/ContractContext.jsx";
import { fmtAlgo, calcScore, fmtScore } from "../utils/format.js";

/* ── Score Arc Gauge ── */
function ScoreGauge({ score }) {
  const size = 200;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  // We use a 270° arc (3/4 circle)
  const arcLength = circumference * 0.75;
  const offset = arcLength - (Math.min(score, 100) / 100) * arcLength;

  const getColor = (s) => {
    if (s >= 70) return "var(--success)";
    if (s >= 40) return "var(--warning)";
    return "var(--danger)";
  };

  const getTier = (s) => {
    if (s >= 70) return { label: "PRIME", color: "var(--success)", bg: "var(--success-dim)" };
    if (s >= 40) return { label: "MODERATE", color: "var(--warning)", bg: "var(--warning-dim)" };
    return { label: "HIGH RISK", color: "var(--danger)", bg: "var(--danger-dim)" };
  };

  const color = getColor(score);
  const tier = getTier(score);

  // Animate from 0
  const [animatedOffset, setAnimatedOffset] = useState(arcLength);
  useEffect(() => {
    const timer = setTimeout(() => setAnimatedOffset(offset), 50);
    return () => clearTimeout(timer);
  }, [offset]);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          style={{ transform: "rotate(135deg)" }}
        >
          {/* Background arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--bg-elevated)"
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeLinecap="round"
          />
          {/* Score arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeDashoffset={animatedOffset}
            strokeLinecap="round"
            style={{
              transition: "stroke-dashoffset 0.8s ease-out, stroke 0.3s ease",
              filter: `drop-shadow(0 0 8px ${color})`,
            }}
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="font-display font-extrabold text-6xl md:text-7xl leading-none"
            style={{ color }}
          >
            {Math.round(score)}
          </span>
          <span
            className="text-[12px] font-sans mt-1"
            style={{ color: "var(--text-muted)" }}
          >
            CREDIT SCORE
          </span>
        </div>
      </div>

      {/* Tier badge */}
      <div
        className="mt-3 px-3 py-1 rounded-[6px] text-[11px] font-sans font-semibold uppercase tracking-wider"
        style={{
          background: tier.bg,
          color: tier.color,
          border: `1px solid ${tier.color}20`,
        }}
      >
        {tier.label}
      </div>
    </div>
  );
}

/* ── Stats Row ── */
function StatsRow({ payments, totalRepaid, creditLimit }) {
  const stats = [
    { label: "PAYMENTS", value: payments, unit: "recorded" },
    { label: "TOTAL REPAID", value: totalRepaid, unit: "ALGO" },
    { label: "CREDIT LIMIT", value: creditLimit, unit: "ALGO" },
  ];

  return (
    <div className="grid grid-cols-3 gap-0 card overflow-hidden">
      {stats.map((s, i) => (
        <div
          key={s.label}
          className="p-4 flex flex-col items-center text-center"
          style={{
            borderRight: i < stats.length - 1 ? "1px solid var(--bg-border)" : "none",
          }}
        >
          <span className="num text-xl md:text-2xl font-semibold text-[var(--text-primary)]">
            {s.value}
          </span>
          <span className="text-[11px] font-sans font-medium uppercase tracking-[0.1em] mt-1" style={{ color: "var(--text-secondary)" }}>
            {s.label}
          </span>
          <span className="text-[10px] font-mono mt-0.5" style={{ color: "var(--text-muted)" }}>
            {s.unit}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ── Credit Multiplier Ladder ── */
function MultiplierLadder({ currentPayments, stake }) {
  const tiers = [
    { payments: 0,  mult: 2 },
    { payments: 1,  mult: 2.5 },
    { payments: 2,  mult: 3 },
    { payments: 3,  mult: 3.5 },
    { payments: 5,  mult: 4.5 },
    { payments: 10, mult: 7 },
    { payments: 16, mult: 10 },
  ];

  const stakeAlgo = Number(stake) / 1e6;
  const cp = Number(currentPayments);

  // Find current tier index
  let currentIdx = 0;
  for (let i = tiers.length - 1; i >= 0; i--) {
    if (cp >= tiers[i].payments) {
      currentIdx = i;
      break;
    }
  }

  return (
    <div className="card p-6">
      <p className="text-[11px] font-sans font-medium uppercase tracking-[0.1em] mb-4" style={{ color: "var(--text-secondary)" }}>
        Credit Multiplier Ladder
      </p>
      <div className="space-y-0">
        {tiers.map((tier, i) => {
          const achieved = cp >= tier.payments;
          const isCurrent = i === currentIdx;
          return (
            <div key={i} className="flex items-center gap-3 py-2 relative">
              {/* Vertical line */}
              {i < tiers.length - 1 && (
                <div
                  className="absolute left-[7px] top-[24px] w-px h-[calc(100%-8px)]"
                  style={{
                    background: achieved ? "var(--accent)" : "var(--bg-border)",
                  }}
                />
              )}
              {/* Dot */}
              <div
                className="w-[15px] h-[15px] rounded-full border-2 shrink-0 z-10 transition-all duration-300"
                style={{
                  borderColor: achieved ? "var(--accent)" : "var(--text-muted)",
                  background: achieved ? "var(--accent)" : "transparent",
                }}
              />
              {/* Content */}
              <div className="flex items-center justify-between flex-1 min-w-0">
                <span className="text-xs font-sans" style={{ color: achieved ? "var(--text-primary)" : "var(--text-muted)" }}>
                  {tier.payments === 0 ? "0 payments" : `${tier.payments} payment${tier.payments > 1 ? "s" : ""}`}
                </span>
                <div className="flex items-center gap-2">
                  <span className="num text-xs font-semibold" style={{ color: achieved ? "var(--accent)" : "var(--text-muted)" }}>
                    {tier.mult}× stake
                  </span>
                  {isCurrent && (
                    <span
                      className="px-1.5 py-0.5 rounded-[4px] text-[9px] font-sans font-semibold uppercase"
                      style={{
                        background: "var(--accent-dim)",
                        color: "var(--accent)",
                        border: "1px solid rgba(99,102,241,0.3)",
                      }}
                    >
                      CURRENT
                    </span>
                  )}
                  {i === tiers.length - 1 && (
                    <span
                      className="px-1.5 py-0.5 rounded-[4px] text-[9px] font-sans font-semibold uppercase"
                      style={{
                        background: "var(--success-dim)",
                        color: "var(--success)",
                        border: "1px solid rgba(34,197,94,0.3)",
                      }}
                    >
                      MAX CAP
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Activity Log ── */
function ActivityLog({ activities }) {
  const EVENT_CONFIG = {
    payment:  { icon: "↑", label: "PAYMENT RECORDED", color: "var(--accent)" },
    draw:     { icon: "→", label: "CREDIT DRAWN",     color: "var(--warning)" },
    repay:    { icon: "←", label: "REPAID",            color: "var(--success)" },
    register: { icon: "✓", label: "REGISTERED",        color: "var(--text-secondary)" },
    slash:    { icon: "✕", label: "SLASHED",            color: "var(--danger)" },
  };

  return (
    <div className="card overflow-hidden">
      <div className="p-4 pb-0">
        <p className="text-[11px] font-sans font-medium uppercase tracking-[0.1em] mb-3" style={{ color: "var(--text-secondary)" }}>
          Recent Activity
        </p>
      </div>
      {activities.length === 0 ? (
        <div className="px-4 py-8 text-center">
          <p className="text-sm font-sans" style={{ color: "var(--text-muted)" }}>
            No activity yet. Register and make your first payment to build history.
          </p>
        </div>
      ) : (
        <div>
          {activities.slice(0, 5).map((act, i) => {
            const cfg = EVENT_CONFIG[act.type] || EVENT_CONFIG.register;
            return (
              <div
                key={i}
                className="flex items-center justify-between px-4 py-3"
                style={{
                  borderBottom: i < activities.length - 1 ? "1px solid var(--bg-border)" : "none",
                }}
              >
                <div className="flex items-center gap-3">
                  <span className="num text-sm font-semibold" style={{ color: cfg.color }}>
                    {cfg.icon}
                  </span>
                  <span className="text-xs font-sans font-medium" style={{ color: cfg.color }}>
                    {cfg.label}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  {act.amount && (
                    <span className="num text-xs text-[var(--text-primary)]">
                      {act.amount}
                    </span>
                  )}
                  {act.round && (
                    <span className="num text-[10px]" style={{ color: "var(--text-muted)" }}>
                      R{act.round}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ── Main ScoreView ── */
export default function ScoreView() {
  const { position, activityLog = [] } = useContract();

  const score = useMemo(() => calcScore(position), [position]);
  const paymentsStr = position.paymentCount.toString();
  const limitStr = fmtAlgo(position.creditLimit);
  // Approximate total repaid from position data
  const stakeAlgo = Number(position.stake) / 1e6;
  const limitAlgo = Number(position.creditLimit) / 1e6;
  const baseLimit = stakeAlgo * 2;
  const repaidEstimate = Math.max(0, (limitAlgo - baseLimit) * 2);
  const repaidStr = repaidEstimate.toFixed(6);

  return (
    <div className="flex flex-col gap-6">
      {/* Hero gauge */}
      <div className="card p-8 flex justify-center">
        {position.isDefaulted ? (
          <div className="flex flex-col items-center py-4">
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center mb-4"
              style={{
                background: "var(--danger-dim)",
                border: "1px solid rgba(239,68,68,0.3)",
              }}
            >
              <span className="text-2xl">⚠</span>
            </div>
            <h3 className="font-display font-bold text-xl mb-1" style={{ color: "var(--danger)" }}>
              DEFAULTED
            </h3>
            <p className="text-sm font-sans" style={{ color: "var(--text-muted)" }}>
              This agent has been slashed. Credit frozen.
            </p>
          </div>
        ) : (
          <ScoreGauge score={score} />
        )}
      </div>

      {/* Stats row */}
      <StatsRow
        payments={paymentsStr}
        totalRepaid={repaidStr}
        creditLimit={limitStr}
      />

      {/* Multiplier ladder */}
      <MultiplierLadder
        currentPayments={position.paymentCount}
        stake={position.stake}
      />

      {/* Activity log */}
      <ActivityLog activities={activityLog} />
    </div>
  );
}
