/**
 * format.js — Display formatting utilities for Bloopa.
 *
 * All ALGO values are stored as microALGO (BigInt or Number).
 * These helpers convert to human-readable display strings.
 */

/**
 * Format microALGO to display string: "1.000000"
 * @param {BigInt|number} micro — value in microALGO
 * @returns {string}
 */
export const fmtAlgo = (micro) => {
  const n = Number(micro) / 1e6;
  return n.toFixed(6);
};

/**
 * Format microALGO with ALGO suffix: "1.000000 ALGO"
 * @param {BigInt|number} micro
 * @returns {string}
 */
export const fmtAlgoFull = (micro) => {
  return fmtAlgo(micro) + " ALGO";
};

/**
 * Format credit score: clamped 0–100, 1 decimal
 * @param {number} n
 * @returns {string}
 */
export const fmtScore = (n) => Math.min(100, Math.max(0, n)).toFixed(1);

/**
 * Truncate an Algorand address: "ABCD...WXYZ"
 * @param {string} addr
 * @param {number} start — chars from start (default 4)
 * @param {number} end — chars from end (default 4)
 * @returns {string}
 */
export const fmtAddress = (addr, start = 4, end = 4) => {
  if (!addr || addr.length < start + end + 3) return addr || "";
  return `${addr.slice(0, start)}...${addr.slice(-end)}`;
};

/**
 * Format round number with # prefix
 * @param {number|BigInt} round
 * @returns {string}
 */
export const fmtRound = (round) => {
  return `#${Number(round).toLocaleString("en-US")}`;
};

/**
 * Format large micro numbers with thin space separators
 * @param {BigInt|number} micro
 * @returns {string}
 */
export const fmtMicro = (micro) => {
  const s = String(Number(micro));
  // Add thin spaces as thousands separator
  return s.replace(/\B(?=(\d{3})+(?!\d))/g, "\u2009");
};

/**
 * Calculate credit score from position data
 * score = min(100, paymentCount*10 + totalRepaid/stake*50)
 * Since we don't have totalRepaid, approximate from paymentCount & limit growth
 */
export const calcScore = (position) => {
  if (!position || position.stake === 0n) return 0;
  const payments = Number(position.paymentCount);
  const stake = Number(position.stake) / 1e6;
  const limit = Number(position.creditLimit) / 1e6;
  const baseLimit = stake * 2;
  const limitGrowth = Math.max(0, limit - baseLimit);
  // Approximate: each payment adds 0.5 ALGO to limit
  const repaidEstimate = limitGrowth * 2; // rough
  const score = Math.min(100, (payments * 10) + (repaidEstimate / stake * 50));
  return Math.max(0, score);
};
