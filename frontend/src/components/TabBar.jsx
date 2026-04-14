/**
 * TabBar.jsx — Two-tab navigation: "Position" | "Score"
 *
 * Active tab: accent underline + primary text
 * Inactive: muted text, hover secondary
 */

import React from "react";

const TABS = [
  { id: "position", label: "Position" },
  { id: "score", label: "Score" },
];

export default function TabBar({ activeTab, onTabChange }) {
  return (
    <div
      className="w-full flex"
      style={{
        background: "var(--bg-surface)",
        borderBottom: "1px solid var(--bg-border)",
      }}
    >
      {TABS.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            id={`tab-${tab.id}`}
            onClick={() => onTabChange(tab.id)}
            className="relative px-6 py-3 font-sans font-medium text-sm transition-colors duration-150"
            style={{
              color: isActive ? "var(--text-primary)" : "var(--text-muted)",
            }}
            onMouseEnter={(e) => {
              if (!isActive) e.currentTarget.style.color = "var(--text-secondary)";
            }}
            onMouseLeave={(e) => {
              if (!isActive) e.currentTarget.style.color = "var(--text-muted)";
            }}
          >
            {tab.label}
            {/* Active indicator line */}
            {isActive && (
              <span
                className="absolute bottom-0 left-0 right-0 h-0.5"
                style={{ background: "var(--accent)" }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
