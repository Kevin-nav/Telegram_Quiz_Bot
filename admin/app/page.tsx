import { AdminShell } from "@/components/admin-shell";

const dashboardCards = [
  {
    label: "Active staff sessions",
    value: "18",
    detail: "2 editors, 1 catalog manager, 1 super admin on deck",
  },
  {
    label: "Question corrections",
    value: "47",
    detail: "Waiting on review before publish",
  },
  {
    label: "Catalog changes",
    value: "12",
    detail: "4 offerings updated in the last 24 hours",
  },
  {
    label: "Analytics anomalies",
    value: "3",
    detail: "Courses with rising failure rates",
  },
];

const reviewQueue = [
  {
    title: "Programming in MATLAB",
    meta: "14 edits pending",
    note: "Correct answer mismatch on matrix indexing item 08.",
  },
  {
    title: "General Psychology",
    meta: "9 edits pending",
    note: "Two explanations need tightening before release.",
  },
  {
    title: "Catalog governance",
    meta: "5 updates pending",
    note: "New level offering awaits publish permission.",
  },
];

const auditTrail = [
  "06:42 - Staff user created for analytics viewer role.",
  "05:31 - Differential Equations explanation corrected and queued.",
  "04:17 - Electrical Engineering first-semester offering marked active.",
];

export default function DashboardPage() {
  return (
    <AdminShell>
      <section className="hero-panel" id="overview">
        <div className="hero-copy">
          <p className="eyebrow">Editorial operations console</p>
          <h1>Control the study catalog like a newsroom controls the edition.</h1>
          <p className="lead">
            Monitor student performance, publish content fixes, and manage the academic
            structure without touching code deployments.
          </p>
        </div>
        <div className="hero-card">
          <div className="hero-card-label">Today&apos;s board</div>
          <div className="hero-card-value">82%</div>
          <div className="hero-card-text">
            of review items are already cached and ready for staff triage.
          </div>
        </div>
      </section>

      <section className="stats-grid" aria-label="Admin metrics">
        {dashboardCards.map((card, index) => (
          <article className="stat-card reveal" style={{ animationDelay: `${index * 90}ms` }} key={card.label}>
            <span className="stat-label">{card.label}</span>
            <strong className="stat-value">{card.value}</strong>
            <span className="stat-detail">{card.detail}</span>
          </article>
        ))}
      </section>

      <section className="content-grid">
        <article className="panel" id="queue">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Review queue</p>
              <h2>Latest content interventions</h2>
            </div>
            <span className="panel-badge">Live</span>
          </div>
          <div className="queue-list">
            {reviewQueue.map((item) => (
              <div className="queue-item" key={item.title}>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.note}</p>
                </div>
                <span>{item.meta}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel" id="audit">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Audit trail</p>
              <h2>Recent staff actions</h2>
            </div>
            <span className="panel-badge muted">Recorded</span>
          </div>
          <div className="timeline">
            {auditTrail.map((entry) => (
              <div className="timeline-item" key={entry}>
                {entry}
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="panel panel-wide" id="catalog">
        <div className="panel-header">
          <div>
            <p className="panel-kicker">Catalog health</p>
            <h2>Database-driven academic structure</h2>
          </div>
          <span className="panel-badge accent">Redis cached</span>
        </div>
        <div className="catalog-tiles">
          <div className="catalog-tile">
            <span>Faculties</span>
            <strong>6</strong>
            <p>Editable without code changes.</p>
          </div>
          <div className="catalog-tile">
            <span>Programs</span>
            <strong>17</strong>
            <p>Linked through canonical offerings.</p>
          </div>
          <div className="catalog-tile">
            <span>Courses</span>
            <strong>64</strong>
            <p>Rendered from the shared catalog cache.</p>
          </div>
        </div>
      </section>
    </AdminShell>
  );
}
