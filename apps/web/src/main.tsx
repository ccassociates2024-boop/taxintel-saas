import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  Bell,
  Building2,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  FileWarning,
  Gauge,
  IndianRupee,
  Landmark,
  LayoutDashboard,
  Lightbulb,
  Menu,
  Moon,
  Search,
  ShieldCheck,
  Sparkles,
  Sun,
  UserRound,
  X,
} from "lucide-react";
import "./styles.css";

type Theme = "light" | "dark";
type PageKey =
  | "overview"
  | "health"
  | "mismatch"
  | "recommendations"
  | "refund"
  | "calendar"
  | "notices";

const navigation = [
  { key: "overview", label: "Client Overview", icon: LayoutDashboard },
  { key: "health", label: "Tax Health Score", icon: Gauge },
  { key: "mismatch", label: "AIS Mismatch Analytics", icon: AlertTriangle },
  { key: "recommendations", label: "Tax-Saving Recommendations", icon: Lightbulb },
  { key: "refund", label: "Refund Tracking", icon: IndianRupee },
  { key: "calendar", label: "Compliance Calendar", icon: CalendarDays },
  { key: "notices", label: "Notice Management", icon: FileWarning },
] satisfies Array<{ key: PageKey; label: string; icon: React.ElementType }>;

const clients = [
  {
    name: "Aarav Mehta",
    pan: "BFXPM4821K",
    type: "Resident Individual",
    owner: "Neha Rao",
    ay: "AY 2026-27",
    health: 86,
    exposure: "₹42.8K",
    refund: "₹18.4K",
    status: "Review ready",
  },
  {
    name: "Ishaan Capital LLP",
    pan: "AAIFI3210Q",
    type: "LLP",
    owner: "Rohan Sethi",
    ay: "AY 2026-27",
    health: 72,
    exposure: "₹1.8L",
    refund: "₹0",
    status: "AIS mismatch",
  },
  {
    name: "Priya Shah",
    pan: "AQHPS9012M",
    type: "NRI",
    owner: "Neha Rao",
    ay: "AY 2026-27",
    health: 91,
    exposure: "₹12.6K",
    refund: "₹62.1K",
    status: "Awaiting docs",
  },
];

const mismatches = [
  { category: "Salary", ais: 1820000, declared: 1800000, severity: "Low", color: "ok" },
  { category: "Interest", ais: 74000, declared: 39000, severity: "Medium", color: "warn" },
  { category: "Capital Gains", ais: 426000, declared: 318000, severity: "High", color: "bad" },
  { category: "Dividend", ais: 28500, declared: 28500, severity: "Clear", color: "ok" },
  { category: "Foreign Remittance", ais: 650000, declared: 0, severity: "High", color: "bad" },
];

const recommendations = [
  { title: "Optimize regime selection", section: "115BAC", impact: "₹32,400", confidence: 94, status: "CA review" },
  { title: "Medical insurance deduction", section: "80D", impact: "₹7,800", confidence: 88, status: "Evidence needed" },
  { title: "Home loan interest check", section: "24(b)", impact: "₹41,200", confidence: 81, status: "Client action" },
  { title: "ELSS cap validation", section: "80C", impact: "₹12,600", confidence: 76, status: "Ready" },
];

const notices = [
  { type: "143(1)", client: "Aarav Mehta", due: "12 May", amount: "₹18.4K", status: "Draft response" },
  { type: "139(9)", client: "Priya Shah", due: "17 May", amount: "N/A", status: "Pending docs" },
  { type: "245", client: "Ishaan Capital LLP", due: "22 May", amount: "₹1.2L", status: "Assigned" },
];

const events = [
  { date: "10 May", title: "Advance tax reconciliation", tag: "Portfolio", risk: "Medium" },
  { date: "12 May", title: "143(1) response deadline", tag: "Notice", risk: "High" },
  { date: "18 May", title: "Client document reminder batch", tag: "Ops", risk: "Low" },
  { date: "25 May", title: "AIS refresh for high-risk clients", tag: "AIS", risk: "Medium" },
];

function App() {
  const [theme, setTheme] = useState<Theme>("light");
  const [activePage, setActivePage] = useState<PageKey>("overview");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const activeLabel = navigation.find((item) => item.key === activePage)?.label ?? "Dashboard";

  const portfolio = useMemo(
    () => ({
      clients: 248,
      review: 37,
      exposure: "₹38.7L",
      refunds: "₹14.2L",
    }),
    [],
  );

  return (
    <div className={`app ${theme}`}>
      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="brand">
          <div className="brandMark">
            <Landmark size={22} />
          </div>
          <div>
            <strong>TaxIntel</strong>
            <span>AI Tax Intelligence</span>
          </div>
          <button className="iconButton sidebarClose" onClick={() => setSidebarOpen(false)} aria-label="Close menu">
            <X size={18} />
          </button>
        </div>

        <nav className="nav">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                className={activePage === item.key ? "navItem active" : "navItem"}
                onClick={() => {
                  setActivePage(item.key);
                  setSidebarOpen(false);
                }}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="tenantCard">
          <Building2 size={18} />
          <div>
            <strong>Rao & Sethi CA</strong>
            <span>Enterprise plan</span>
          </div>
        </div>
      </aside>

      <div className="shell">
        <header className="topbar">
          <button className="iconButton menuButton" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
            <Menu size={20} />
          </button>
          <div>
            <p className="eyebrow">Workspace</p>
            <h1>{activeLabel}</h1>
          </div>
          <div className="topbarActions">
            <label className="search">
              <Search size={17} />
              <input placeholder="Search clients, PAN, notices" />
            </label>
            <button className="iconButton" aria-label="Notifications">
              <Bell size={19} />
              <span className="dot" />
            </button>
            <button
              className="iconButton"
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
              aria-label="Toggle theme"
            >
              {theme === "light" ? <Moon size={19} /> : <Sun size={19} />}
            </button>
            <div className="avatar">
              <UserRound size={18} />
            </div>
          </div>
        </header>

        <main className="content">
          {activePage === "overview" && <ClientOverview portfolio={portfolio} />}
          {activePage === "health" && <TaxHealth />}
          {activePage === "mismatch" && <MismatchAnalytics />}
          {activePage === "recommendations" && <Recommendations />}
          {activePage === "refund" && <RefundTracking />}
          {activePage === "calendar" && <ComplianceCalendar />}
          {activePage === "notices" && <NoticeManagement />}
        </main>
      </div>
    </div>
  );
}

function ClientOverview({ portfolio }: { portfolio: { clients: number; review: number; exposure: string; refunds: string } }) {
  return (
    <>
      <section className="metricGrid">
        <Metric icon={UserRound} label="Active clients" value={portfolio.clients} trend="+18 this month" tone="blue" />
        <Metric icon={ClipboardList} label="Pending reviews" value={portfolio.review} trend="9 due today" tone="amber" />
        <Metric icon={AlertTriangle} label="Tax exposure" value={portfolio.exposure} trend="-12% vs last cycle" tone="red" />
        <Metric icon={IndianRupee} label="Refund pipeline" value={portfolio.refunds} trend="+₹2.1L released" tone="green" />
      </section>

      <section className="dashboardGrid twoCol">
        <Panel title="Client Portfolio" action="View all">
          <div className="clientList">
            {clients.map((client) => (
              <div className="clientRow" key={client.pan}>
                <div className="clientIdentity">
                  <div className="scoreBubble" style={{ "--score": `${client.health}%` } as React.CSSProperties}>
                    {client.health}
                  </div>
                  <div>
                    <strong>{client.name}</strong>
                    <span>{client.pan} · {client.type}</span>
                  </div>
                </div>
                <div className="rowMeta">
                  <span>{client.owner}</span>
                  <strong>{client.status}</strong>
                </div>
                <ChevronRight size={18} />
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Risk Distribution">
          <div className="riskStack">
            <div style={{ width: "48%" }} className="riskSegment low">Low</div>
            <div style={{ width: "31%" }} className="riskSegment medium">Medium</div>
            <div style={{ width: "21%" }} className="riskSegment high">High</div>
          </div>
          <div className="insightList">
            <Insight icon={ShieldCheck} title="182 clients are filing-ready" detail="Computation, AIS, and 26AS checks are aligned." />
            <Insight icon={AlertTriangle} title="19 high-priority mismatches" detail="Capital gains and foreign remittance need CA review." />
            <Insight icon={Sparkles} title="₹8.6L estimated savings" detail="AI recommendations awaiting evidence validation." />
          </div>
        </Panel>
      </section>
    </>
  );
}

function TaxHealth() {
  const factors = [
    ["AIS alignment", 78],
    ["26AS reconciliation", 92],
    ["Deduction evidence", 68],
    ["Notice exposure", 84],
    ["Refund confidence", 88],
  ] as const;

  return (
    <section className="dashboardGrid healthGrid">
      <Panel title="Tax Health Score">
        <div className="healthHero">
          <div className="healthRing" style={{ "--score": "86%" } as React.CSSProperties}>
            <strong>86</strong>
            <span>Healthy</span>
          </div>
          <div className="healthNarrative">
            <h2>Aarav Mehta</h2>
            <p>Risk is concentrated in capital gains evidence and one interest-income mismatch.</p>
            <div className="statusPills">
              <span className="pill good">Computation stable</span>
              <span className="pill warn">Evidence pending</span>
              <span className="pill good">Refund likely</span>
            </div>
          </div>
        </div>
      </Panel>
      <Panel title="Score Drivers">
        <div className="barList">
          {factors.map(([label, value]) => (
            <Bar key={label} label={label} value={value} />
          ))}
        </div>
      </Panel>
    </section>
  );
}

function MismatchAnalytics() {
  const max = Math.max(...mismatches.map((item) => item.ais));
  return (
    <section className="dashboardGrid twoCol">
      <Panel title="AIS vs Declared">
        <div className="mismatchChart">
          {mismatches.map((item) => (
            <div className="mismatchItem" key={item.category}>
              <div className="mismatchHead">
                <span>{item.category}</span>
                <strong className={item.color}>{item.severity}</strong>
              </div>
              <div className="compareBars">
                <span className="aisBar" style={{ width: `${(item.ais / max) * 100}%` }} />
                <span className="declaredBar" style={{ width: `${(item.declared / max) * 100}%` }} />
              </div>
              <div className="mismatchValues">
                <span>AIS ₹{formatNumber(item.ais)}</span>
                <span>Declared ₹{formatNumber(item.declared)}</span>
              </div>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Mismatch Actions">
        <div className="actionQueue">
          <ActionItem title="Foreign remittance not declared" amount="₹6.5L" priority="High" />
          <ActionItem title="Broker capital gains differ from AIS" amount="₹1.08L" priority="High" />
          <ActionItem title="Savings interest missing from computation" amount="₹35K" priority="Medium" />
          <ActionItem title="Salary variance within threshold" amount="₹20K" priority="Low" />
        </div>
      </Panel>
    </section>
  );
}

function Recommendations() {
  return (
    <section className="dashboardGrid twoCol">
      <Panel title="Tax-Saving Recommendations">
        <div className="recommendationList">
          {recommendations.map((item) => (
            <div className="recommendation" key={item.title}>
              <div className="recIcon">
                <Lightbulb size={18} />
              </div>
              <div>
                <strong>{item.title}</strong>
                <span>{item.section} · Confidence {item.confidence}%</span>
              </div>
              <div className="recImpact">
                <strong>{item.impact}</strong>
                <span>{item.status}</span>
              </div>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Savings Forecast">
        <div className="forecast">
          <strong>₹94,000</strong>
          <span>Potential verified tax benefit</span>
          <div className="forecastGrid">
            <SmallStat label="Ready" value="₹12.6K" />
            <SmallStat label="Needs proof" value="₹49.0K" />
            <SmallStat label="CA review" value="₹32.4K" />
          </div>
        </div>
      </Panel>
    </section>
  );
}

function RefundTracking() {
  return (
    <section className="dashboardGrid twoCol">
      <Panel title="Refund Pipeline">
        <div className="timeline">
          {["ITR filed", "CPC processing", "Refund approved", "Bank credit"].map((step, index) => (
            <div className={`timelineStep ${index < 3 ? "done" : ""}`} key={step}>
              <CheckCircle2 size={18} />
              <div>
                <strong>{step}</strong>
                <span>{index < 3 ? "Completed" : "Expected in 5-7 days"}</span>
              </div>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Refund Summary">
        <div className="refundCard">
          <span>Estimated refund</span>
          <strong>₹18,400</strong>
          <p>TDS credit and computation agree. Bank validation is complete.</p>
          <div className="statusPills">
            <span className="pill good">26AS matched</span>
            <span className="pill good">No demand</span>
          </div>
        </div>
      </Panel>
    </section>
  );
}

function ComplianceCalendar() {
  return (
    <section className="dashboardGrid twoCol">
      <Panel title="Compliance Calendar">
        <div className="calendarList">
          {events.map((event) => (
            <div className="calendarEvent" key={event.title}>
              <div className="dateBox">{event.date}</div>
              <div>
                <strong>{event.title}</strong>
                <span>{event.tag}</span>
              </div>
              <span className={`riskLabel ${event.risk.toLowerCase()}`}>{event.risk}</span>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="SLA Monitor">
        <div className="slaGrid">
          <SmallStat label="Due this week" value="21" />
          <SmallStat label="At risk" value="6" />
          <SmallStat label="Overdue" value="2" />
          <SmallStat label="Auto-reminders" value="148" />
        </div>
      </Panel>
    </section>
  );
}

function NoticeManagement() {
  return (
    <section className="dashboardGrid twoCol">
      <Panel title="Notice Queue">
        <div className="noticeTable">
          {notices.map((notice) => (
            <div className="noticeRow" key={`${notice.type}-${notice.client}`}>
              <div>
                <strong>{notice.type}</strong>
                <span>{notice.client}</span>
              </div>
              <div>
                <strong>{notice.due}</strong>
                <span>Due date</span>
              </div>
              <div>
                <strong>{notice.amount}</strong>
                <span>Demand</span>
              </div>
              <span className="pill warn">{notice.status}</span>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="AI Litigation Assistant">
        <div className="assistantPanel">
          <Sparkles size={28} />
          <h2>Draft readiness: 72%</h2>
          <p>One notice has extracted DIN, issue section, demand amount, and response chronology ready for CA review.</p>
          <button className="primaryButton">Open draft queue</button>
        </div>
      </Panel>
    </section>
  );
}

function Metric({ icon: Icon, label, value, trend, tone }: { icon: React.ElementType; label: string; value: string | number; trend: string; tone: string }) {
  return (
    <div className={`metric ${tone}`}>
      <div className="metricTop">
        <Icon size={20} />
        <span>{label}</span>
      </div>
      <strong>{value}</strong>
      <small>{trend}</small>
    </div>
  );
}

function Panel({ title, action, children }: { title: string; action?: string; children: React.ReactNode }) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>{title}</h2>
        {action && <button className="textButton">{action}</button>}
      </div>
      {children}
    </section>
  );
}

function Insight({ icon: Icon, title, detail }: { icon: React.ElementType; title: string; detail: string }) {
  return (
    <div className="insight">
      <Icon size={18} />
      <div>
        <strong>{title}</strong>
        <span>{detail}</span>
      </div>
    </div>
  );
}

function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div className="barRow">
      <div>
        <span>{label}</span>
        <strong>{value}%</strong>
      </div>
      <div className="track">
        <span style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function ActionItem({ title, amount, priority }: { title: string; amount: string; priority: string }) {
  return (
    <div className="actionItem">
      <AlertTriangle size={18} />
      <div>
        <strong>{title}</strong>
        <span>{priority} priority</span>
      </div>
      <strong>{amount}</strong>
    </div>
  );
}

function SmallStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="smallStat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value);
}

createRoot(document.getElementById("root")!).render(<App />);
