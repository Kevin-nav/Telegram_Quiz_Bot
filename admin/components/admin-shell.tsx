import Link from "next/link";
import type { ReactNode } from "react";

const sections = [
  { href: "#overview", label: "Overview" },
  { href: "#queue", label: "Queue" },
  { href: "#catalog", label: "Catalog" },
  { href: "#audit", label: "Audit" },
];

export function AdminShell({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
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
            {sections.map((section) => (
              <Link href={section.href} key={section.href}>
                <span>{section.label}</span>
                <span aria-hidden="true">↗</span>
              </Link>
            ))}
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
