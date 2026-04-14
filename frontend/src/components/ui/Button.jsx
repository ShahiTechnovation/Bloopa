/**
 * Button.jsx — Shared button primitive for Bloopa.
 *
 * Variants: primary | danger | ghost | outline
 * Sizes: sm | md | lg
 * States: idle, hover, loading, disabled
 */

import React from "react";

const VARIANTS = {
  primary: {
    base: "bg-[var(--accent)] text-[var(--text-primary)]",
    hover: "hover:bg-[var(--accent-hover)] hover:shadow-[0_0_20px_rgba(99,102,241,0.15)]",
    disabled: "opacity-40 cursor-not-allowed",
  },
  danger: {
    base: "bg-transparent border border-[var(--danger)] text-[var(--danger)]",
    hover: "hover:bg-[var(--danger)] hover:text-white",
    disabled: "opacity-40 cursor-not-allowed",
  },
  ghost: {
    base: "bg-transparent text-[var(--text-secondary)]",
    hover: "hover:bg-[var(--bg-elevated)] hover:text-[var(--text-primary)]",
    disabled: "opacity-40 cursor-not-allowed",
  },
  outline: {
    base: "bg-transparent border border-[var(--bg-border)] text-[var(--text-primary)]",
    hover: "hover:border-[var(--accent)] hover:text-[var(--accent)]",
    disabled: "opacity-40 cursor-not-allowed",
  },
};

const SIZES = {
  sm: "h-8 px-3 text-xs rounded-[6px]",
  md: "h-10 px-4 text-sm rounded-[8px]",
  lg: "h-12 px-6 text-sm rounded-[8px]",
};

function Spinner() {
  return (
    <svg
      className="spinner w-5 h-5"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle
        cx="12" cy="12" r="10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        opacity="0.25"
      />
      <path
        d="M12 2a10 10 0 019.95 9"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  children,
  className = "",
  id,
  ...props
}) {
  const v = VARIANTS[variant] || VARIANTS.primary;
  const s = SIZES[size] || SIZES.md;
  const isDisabled = disabled && !loading;

  return (
    <button
      id={id}
      disabled={isDisabled}
      className={[
        "inline-flex items-center justify-center gap-2",
        "font-sans font-semibold",
        "transition-all duration-150 ease-in-out",
        "active:scale-[0.98]",
        s,
        v.base,
        isDisabled ? v.disabled : v.hover,
        isDisabled && "pointer-events-none",
        className,
      ].filter(Boolean).join(" ")}
      {...props}
    >
      {loading ? (
        <>
          <Spinner />
          <span>Signing...</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}
