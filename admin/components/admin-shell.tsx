"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const sections = [
  { href: "/", label: "Overview" },
  { href: "/staff", label: "Staff" },
  { href: "/catalog", label: "Catalog" },
  { href: "/questions", label: "Questions" },
  { href: "/audit", label: "Audit" },
];

export function AdminShell({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  const pathname = usePathname();

  return (
    <div className="app-shell">
      <div className="shell-frame">
        <aside className="shell-rail">
          <div className="brand-mark">Adarkwa / Admin</div>
          <p className="rail-copy">
            Editorial-grade control surface for the bot, the catalog, and the question
            bank.
          </p>
          <nav className="rail-nav" aria-label="Dashboard sections">
            {sections.map((section) => {
              const isActive = pathname === section.href;
              return (
                <Link
                  aria-current={isActive ? "page" : undefined}
                  href={section.href}
                  key={section.href}
                >
                  <span>{section.label}</span>
                  <span aria-hidden="true">{isActive ? "Current" : "Open"}</span>
                </Link>
              );
            })}
          </nav>
          <div className="rail-meta">
            <span>Operations status</span>
            <strong>Ready</strong>
          </div>
        </aside>

        <section className="shell-main">
          <header className="topbar">
            <div>
              <div className="topbar-label">Admin subdomain</div>
              <div className="topbar-title">Content, analytics, and catalog governance</div>
            </div>
            <div className="topbar-chip">Staff session protected</div>
          </header>

          <div className="content-stack">{children}</div>
        </section>
      </div>
    </div>
  );
}
