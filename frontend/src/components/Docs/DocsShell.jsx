/**
 * DocsShell.jsx — Top-level docs wrapper.
 * Combines DocsLayout + DocsPage.
 */
import React, { useState } from "react";
import DocsLayout from "./DocsLayout.jsx";
import DocsPage from "./DocsPage.jsx";

export default function DocsShell() {
  const [activePage, setActivePage] = useState("introduction");

  return (
    <DocsLayout activePage={activePage} onNavigate={setActivePage}>
      <DocsPage activePage={activePage} onNavigate={setActivePage} />
    </DocsLayout>
  );
}
