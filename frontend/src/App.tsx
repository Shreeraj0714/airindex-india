import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity, AlertTriangle, BarChart3, BookOpen, ChevronRight, CircleDollarSign,
  Database, Info, LineChart as LineChartIcon, LoaderCircle, Radar, RefreshCw,
  Route, ShieldCheck, SlidersHorizontal, Sparkles, TrendingDown, TrendingUp,
} from "lucide-react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "./api";
import type { Airline, ChartPoint, LeadPoint, RouteIndex, Shock, Summary } from "./types";

type View = "overview" | "index" | "routes" | "airlines" | "lead" | "shocks" | "forecast" | "traveller" | "scenario" | "quality" | "method";
type ApiData<T> = { available: boolean; data: T[]; message?: string };

const nav: { id: View; label: string; icon: typeof Activity }[] = [
  { id: "overview", label: "Overview", icon: Activity }, { id: "index", label: "Airfare Index", icon: LineChartIcon },
  { id: "routes", label: "Route Intelligence", icon: Route }, { id: "airlines", label: "Airlines", icon: BarChart3 },
  { id: "lead", label: "Lead-Time", icon: TrendingUp }, { id: "shocks", label: "Market Shocks", icon: AlertTriangle },
  { id: "forecast", label: "Forecast", icon: Radar }, { id: "traveller", label: "Traveller Mode", icon: BookOpen },
  { id: "scenario", label: "Scenario Simulator", icon: SlidersHorizontal }, { id: "quality", label: "Data Quality", icon: ShieldCheck },
  { id: "method", label: "Methodology", icon: Info },
];

const colors = ["#50e3c2", "#67a4ff", "#f9bb52", "#9e8cff", "#ff7e77", "#22a7f0", "#5dd48d", "#d876ff", "#ff9f68", "#76d9de"];
const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const signed = (value?: number) => `${(value || 0) >= 0 ? "+" : ""}${(value || 0).toFixed(2)}`;

function Empty({ message }: { message?: string }) {
  return <div className="empty"><Database size={25} /><p>{message || "Initialize the development / replay dataset to calculate this view."}</p></div>;
}

function Card({ label, value, change, icon: Icon, tone = "blue" }: { label: string; value: string; change?: string; icon: typeof Activity; tone?: "blue" | "green" | "amber" | "violet" }) {
  return <div className="metric-card"><div><p className="eyebrow">{label}</p><p className="metric-value">{value}</p>{change && <p className={`metric-change ${change.startsWith("+") ? "positive" : change.startsWith("−") || change.startsWith("-") ? "negative" : ""}`}>{change}</p>}</div><span className={`icon-box ${tone}`}><Icon size={20} /></span></div>;
}

function ChartPanel({ title, subtitle, children, className = "" }: { title: string; subtitle?: string; children: React.ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><div className="panel-header"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div><span className="live-dot">CALCULATED</span></div>{children}</section>;
}

function App() {
  const [view, setView] = useState<View>("overview");
  const [summary, setSummary] = useState<Summary>({ available: false });
  const [series, setSeries] = useState<ChartPoint[]>([]);
  const [routes, setRoutes] = useState<RouteIndex[]>([]);
  const [contributions, setContributions] = useState<RouteIndex[]>([]);
  const [lead, setLead] = useState<LeadPoint[]>([]);
  const [airlines, setAirlines] = useState<Airline[]>([]);
  const [shocks, setShocks] = useState<Shock[]>([]);
  const [quality, setQuality] = useState<Record<string, number | string | string[] | boolean> | null>(null);
  const [forecast, setForecast] = useState<Record<string, string | number | boolean> | null>(null);
  const [explanation, setExplanation] = useState<{ message?: string; evidence?: { metric: string; value: number }[] }>({});
  const [meta, setMeta] = useState<{ routes: string[]; lead_windows: number[]; weight_note: string; source_note: string } | null>(null);
  const [selectedRoute, setSelectedRoute] = useState("DEL-BOM");
  const [loading, setLoading] = useState(true);
  const [initializing, setInitializing] = useState(false);
  const [error, setError] = useState("");
  const [decision, setDecision] = useState<Record<string, unknown> | null>(null);
  const [scenario, setScenario] = useState<Record<string, unknown> | null>(null);
  const [fareInput, setFareInput] = useState("");
  const [advance, setAdvance] = useState("7");
  const [scenarioChange, setScenarioChange] = useState("10");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [s, ni, ri, ci, lt, al, an, q, fc, ex, md] = await Promise.all([
        api<Summary>("/summary"), api<ApiData<ChartPoint>>("/index"), api<ApiData<RouteIndex>>("/index/routes"),
        api<ApiData<RouteIndex>>("/index/contribution"), api<ApiData<LeadPoint>>("/lead-time"), api<ApiData<Airline>>("/airlines"),
        api<ApiData<Shock>>("/analytics/anomalies"), api<Record<string, number | string | string[] | boolean>>("/quality"),
        api<Record<string, string | number | boolean>>("/forecast"), api<{ message?: string; evidence?: { metric: string; value: number }[]}>("/analytics/explanations"),
        api<{ routes: string[]; lead_windows: number[]; weight_note: string; source_note: string }>("/metadata"),
      ]);
      setSummary(s); setSeries(ni.data || []); setRoutes(ri.data || []); setContributions(ci.data || []); setLead(lt.data || []); setAirlines(al.data || []); setShocks(an.data || []); setQuality(q); setForecast(fc); setExplanation(ex); setMeta(md);
    } catch (err) { setError(err instanceof Error ? err.message : "The dashboard could not reach the API."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!summary.available) return;
    api<ApiData<LeadPoint>>(`/lead-time?route=${selectedRoute}`).then(response => setLead(response.data || [])).catch(() => undefined);
    api<{ message?: string; evidence?: { metric: string; value: number }[]}>(`/analytics/explanations?route=${selectedRoute}`).then(setExplanation).catch(() => undefined);
  }, [selectedRoute, summary.available]);

  async function initialize() {
    setInitializing(true); setError("");
    try { await api("/seed", { method: "POST" }); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Dataset initialization failed."); }
    finally { setInitializing(false); }
  }

  async function getDecision(event: React.FormEvent) {
    event.preventDefault();
    try { setDecision(await api("/decision-support", { method: "POST", body: JSON.stringify({ route: selectedRoute, advance_days: Number(advance), current_fare: fareInput ? Number(fareInput) : undefined }) })); }
    catch (err) { setError(err instanceof Error ? err.message : "Decision support was unavailable."); }
  }

  async function runScenario(event: React.FormEvent) {
    event.preventDefault();
    try { setScenario(await api("/scenario", { method: "POST", body: JSON.stringify({ route: selectedRoute, fare_change_pct: Number(scenarioChange) }) })); }
    catch (err) { setError(err instanceof Error ? err.message : "Scenario could not be calculated."); }
  }

  const activeRoute = useMemo(() => routes.find(item => item.route === selectedRoute), [routes, selectedRoute]);
  const severityClass = (severity: string) => severity.toLowerCase();

  function Dashboard() {
    if (!summary.available) return <Empty message={summary.message} />;
    return <>
      <div className="metric-grid">
        <Card label="National Airfare Index" value={summary.national_index?.toFixed(2) || "—"} change="Base period = 100" icon={Activity} tone="blue" />
        <Card label="Daily Change" value={`${signed(summary.daily_change)} pts`} change={summary.daily_change && summary.daily_change > 0 ? "↑ latest calculated movement" : "↓ latest calculated movement"} icon={summary.daily_change && summary.daily_change >= 0 ? TrendingUp : TrendingDown} tone="green" />
        <Card label="Data Quality" value={`${summary.data_quality?.toFixed(1) || "—"}%`} change="validity + robust outlier flags" icon={ShieldCheck} tone="violet" />
        <Card label="Replay Observations" value={(summary.observations || 0).toLocaleString("en-IN")} change={`${summary.available_observations || 0} currently available`} icon={Database} tone="amber" />
      </div>
      <div className="dashboard-grid primary-grid">
        <ChartPanel title="National Index Trend" subtitle="Daily Laspeyres-style weighted relative price index" className="span-2">
          <div className="chart tall"><ResponsiveContainer width="100%" height="100%"><AreaChart data={series}><defs><linearGradient id="indexArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#50e3c2" stopOpacity={.36}/><stop offset="100%" stopColor="#50e3c2" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#23334d" vertical={false}/><XAxis dataKey="date" tick={{ fill: "#7f94b1", fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={32}/><YAxis domain={["dataMin - 1", "dataMax + 1"]} tick={{ fill: "#7f94b1", fontSize: 11 }} tickLine={false} axisLine={false}/><Tooltip contentStyle={{ background: "#0d1c33", border: "1px solid #2b4162", borderRadius: 10 }}/><Area type="monotone" dataKey="index" stroke="#50e3c2" strokeWidth={2.5} fill="url(#indexArea)" /></AreaChart></ResponsiveContainer></div>
        </ChartPanel>
        <ChartPanel title="Short-term Outlook" subtitle="Explainable baseline; not a guarantee">
          {forecast?.available ? <div className="forecast-card"><p className={`forecast-direction ${forecast.direction === "INCREASE" ? "up" : "down"}`}>{String(forecast.direction)}</p><p className="forecast-number">{Number(forecast.expected_change_pct) >= 0 ? "+" : ""}{String(forecast.expected_change_pct)}%</p><p>Expected 7-day national index change</p><div className="forecast-meta"><span>Confidence <b>{String(forecast.confidence)}</b></span><span>MAE <b>{String(forecast.model_error_mae)} pts</b></span></div></div> : <Empty message={String(forecast?.message || "Forecast unavailable.")} />}
        </ChartPanel>
      </div>
      <div className="dashboard-grid three-grid">
        <ChartPanel title="Route Contribution" subtitle="Index points since base period">
          <div className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={contributions.slice(0, 6)} layout="vertical" margin={{ left: 4 }}><XAxis type="number" tick={{ fill: "#7f94b1", fontSize: 10 }} axisLine={false} tickLine={false}/><YAxis type="category" dataKey="route" width={58} tick={{ fill: "#b9c8dd", fontSize: 11 }} axisLine={false} tickLine={false}/><Tooltip contentStyle={{ background: "#0d1c33", border: "1px solid #2b4162", borderRadius: 10 }}/><Bar dataKey="contribution_points" radius={[0, 4, 4, 0]} fill="#67a4ff" /></BarChart></ResponsiveContainer></div>
        </ChartPanel>
        <ChartPanel title="Lead-Time Curve" subtitle="Observed latest fares by booking window">
          <div className="chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={lead}><CartesianGrid stroke="#23334d" vertical={false}/><XAxis dataKey="label" tick={{ fill: "#7f94b1", fontSize: 11 }} axisLine={false} tickLine={false}/><YAxis tick={{ fill: "#7f94b1", fontSize: 10 }} axisLine={false} tickLine={false} width={44}/><Tooltip formatter={(value: number) => inr.format(value)} contentStyle={{ background: "#0d1c33", border: "1px solid #2b4162", borderRadius: 10 }}/><Line type="monotone" dataKey="current_fare" stroke="#f9bb52" strokeWidth={2.5} dot={{ r: 3 }} /></LineChart></ResponsiveContainer></div>
        </ChartPanel>
        <ChartPanel title="Market Shock Feed" subtitle="Robust historical movement thresholds">
          <div className="shock-list">{shocks.slice(0, 4).map(item => <div className="shock" key={item.route}><span className={`severity ${severityClass(item.severity)}`}>{item.severity}</span><b>{item.route}</b><span className={item.change_pct >= 0 ? "positive" : "negative"}>{signed(item.change_pct)}%</span></div>)}</div>
        </ChartPanel>
      </div>
    </>;
  }

  function IndexView() { return <div className="dashboard-grid split-grid"><ChartPanel title="National Airfare Price Index" subtitle="Choose daily, weekly or monthly API series in the data pipeline" className="span-2"><div className="chart tall"><ResponsiveContainer width="100%" height="100%"><LineChart data={series}><CartesianGrid stroke="#23334d" vertical={false}/><XAxis dataKey="date" tick={{ fill: "#7f94b1", fontSize: 11 }} axisLine={false} tickLine={false} minTickGap={30}/><YAxis tick={{ fill: "#7f94b1", fontSize: 11 }} axisLine={false} tickLine={false}/><Tooltip contentStyle={{ background: "#0d1c33", border: "1px solid #2b4162", borderRadius: 10 }}/><Line dataKey="index" stroke="#50e3c2" strokeWidth={3} dot={false}/></LineChart></ResponsiveContainer></div></ChartPanel><ChartPanel title="Prototype Basket" subtitle="Configurable route weights"><div className="weight-list">{routes.map(item => <div key={item.route}><span>{item.route}</span><b>{(item.weight * 100).toFixed(0)}%</b><i style={{ width: `${item.weight * 100 * 4}%`}} /></div>)}</div></ChartPanel><ChartPanel title="Formula & Scope" subtitle="Transparent computation" className="span-2"><div className="formula"><code>Indexₜ = 100 × Σ(wᵢ × Pᵢ,ₜ / Pᵢ,base)</code><p>Each route uses its mean normalized core fare (base fare + taxes + mandatory fees). Sold-out flights are excluded from price aggregation and retained as an availability state.</p><p className="disclaimer">{meta?.weight_note}</p></div></ChartPanel></div>; }

  function RoutesView() { return <><div className="route-toolbar"><label>Route <select value={selectedRoute} onChange={e => setSelectedRoute(e.target.value)}>{meta?.routes.map(route => <option key={route}>{route}</option>)}</select></label>{activeRoute && <div className="route-stat"><span>Latest index</span><b>{activeRoute.index.toFixed(2)}</b><span>Latest mean</span><b>{inr.format(activeRoute.current_fare)}</b></div>}</div><div className="dashboard-grid split-grid"><ChartPanel title={`${selectedRoute} Lead-Time Intelligence`} subtitle="Observed current and historical comparable lead-time fares" className="span-2"><div className="chart tall"><ResponsiveContainer width="100%" height="100%"><BarChart data={lead}><CartesianGrid stroke="#23334d" vertical={false}/><XAxis dataKey="label" tick={{fill:"#7f94b1"}} axisLine={false} tickLine={false}/><YAxis tick={{fill:"#7f94b1"}} axisLine={false} tickLine={false}/><Tooltip formatter={(value: number) => inr.format(value)} contentStyle={{background:"#0d1c33",border:"1px solid #2b4162",borderRadius:10}}/><Legend/><Bar dataKey="current_fare" name="Latest replay fare" fill="#50e3c2" radius={[4,4,0,0]}/><Bar dataKey="historical_median" name="Historical median" fill="#496d9f" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></div></ChartPanel><ChartPanel title="Evidence-based explanation" subtitle="No external causes are inferred"><p className="explanation">{explanation.message}</p><div className="evidence">{explanation.evidence?.map(item => <span key={item.metric}><small>{item.metric}</small><b>{typeof item.value === "number" && item.metric.includes("fare") ? inr.format(item.value) : item.value}</b></span>)}</div></ChartPanel></div><ChartPanel title="Route-network basket" subtitle="Logical connections only — not a geographically accurate map"><div className="network">{routes.map((route, index) => <div className="network-route" key={route.route}><span className="node">{route.route.slice(0, 3)}</span><i style={{ backgroundColor: colors[index] }}/><b>{route.route}</b><i style={{ backgroundColor: colors[index] }}/><span className="node">{route.route.slice(4)}</span><em>{route.index.toFixed(1)}</em></div>)}</div></ChartPanel></>; }

  function AirlinesView() { return <ChartPanel title="Airline Comparison" subtitle="Latest available development / replay observations"><div className="chart very-tall"><ResponsiveContainer width="100%" height="100%"><BarChart data={airlines}><CartesianGrid stroke="#23334d" vertical={false}/><XAxis dataKey="airline" tick={{fill:"#b9c8dd"}} axisLine={false} tickLine={false}/><YAxis tick={{fill:"#7f94b1"}} axisLine={false} tickLine={false}/><Tooltip formatter={(value: number) => inr.format(value)} contentStyle={{background:"#0d1c33",border:"1px solid #2b4162",borderRadius:10}}/><Bar dataKey="average_fare" name="Mean core fare" radius={[6,6,0,0]}>{airlines.map((item, i) => <Cell key={item.airline} fill={colors[i]} />)}</Bar></BarChart></ResponsiveContainer></div></ChartPanel>; }

  function LeadView() { return <><div className="route-toolbar"><label>Compare route <select value={selectedRoute} onChange={e => setSelectedRoute(e.target.value)}><option value="">National basket</option>{meta?.routes.map(route => <option key={route}>{route}</option>)}</select></label></div><ChartPanel title="Advance Purchase Windows" subtitle="The curve reports observation, rather than assuming that booking earlier is always cheaper."><div className="chart very-tall"><ResponsiveContainer width="100%" height="100%"><LineChart data={lead}><CartesianGrid stroke="#23334d" vertical={false}/><XAxis dataKey="label" tick={{fill:"#b9c8dd"}} axisLine={false} tickLine={false}/><YAxis tick={{fill:"#7f94b1"}} axisLine={false} tickLine={false}/><Tooltip formatter={(value: number) => inr.format(value)} contentStyle={{background:"#0d1c33",border:"1px solid #2b4162",borderRadius:10}}/><Legend/><Line type="monotone" dataKey="current_fare" name="Latest observed fare" stroke="#f9bb52" strokeWidth={3}/><Line type="monotone" dataKey="historical_median" name="Historical median" stroke="#5c82b6" strokeWidth={2}/></LineChart></ResponsiveContainer></div></ChartPanel></>; }

  function ShocksView() { return <ChartPanel title="Market Shock Detection" subtitle="A price shock is a route-level movement against robust history—not simply a high fare."><div className="data-table"><div className="table-row table-head"><span>Route</span><span>Current fare</span><span>Historical reference</span><span>Change</span><span>Classification</span></div>{shocks.map(item => <div className="table-row" key={item.route}><b>{item.route}</b><span>{inr.format(item.current_fare)}</span><span>{inr.format(item.historical_reference)}</span><span className={item.change_pct >= 0 ? "positive" : "negative"}>{signed(item.change_pct)}%</span><span className={`severity ${severityClass(item.severity)}`}>{item.severity}</span></div>)}</div></ChartPanel>; }

  function ForecastView() { return <div className="dashboard-grid split-grid"><ChartPanel title="Short-term Airfare Forecast" subtitle="Transparent baseline forecast"><div className="forecast-detail">{forecast?.available ? <><p className="forecast-direction">{String(forecast.direction)}</p><strong>{Number(forecast.expected_change_pct) >= 0 ? "+" : ""}{String(forecast.expected_change_pct)}%</strong><p>Expected next-period national movement</p><div><span>Current index <b>{String(forecast.current_index)}</b></span><span>Projected index <b>{String(forecast.forecast_index)}</b></span><span>Uncertainty band <b>±{String(forecast.uncertainty_band)} points</b></span></div></> : <Empty message={String(forecast?.message)} />}</div></ChartPanel><ChartPanel title="Model transparency" subtitle="Forecasting is an enhancement, not the index"><ul className="method-list"><li><b>Model:</b> {String(forecast?.model || "Unavailable")}</li><li><b>Backtest proxy:</b> mean absolute day-to-day error of {String(forecast?.model_error_mae || "—")} index points.</li><li><b>Interpretation:</b> {String(forecast?.message || "No forecast data available.")}</li></ul></ChartPanel></div>; }

  function TravellerView() { return <div className="dashboard-grid split-grid"><ChartPanel title="Book / Monitor / Wait" subtitle="Evidence-led traveller decision support"><form className="form" onSubmit={getDecision}><label>Route<select value={selectedRoute} onChange={e => setSelectedRoute(e.target.value)}>{meta?.routes.map(route => <option key={route}>{route}</option>)}</select></label><label>Advance days<input type="number" min="0" max="365" value={advance} onChange={e => setAdvance(e.target.value)}/></label><label>Current fare (optional)<input type="number" min="1" placeholder="Use replay latest fare" value={fareInput} onChange={e => setFareInput(e.target.value)}/></label><button className="primary" type="submit"><Sparkles size={16}/> Assess fare</button></form></ChartPanel><ChartPanel title="Recommendation" subtitle="Decision support only; never a guarantee">{decision ? <div className="decision"><p className="decision-label">{String(decision.recommendation)}</p><p>{String(decision.message)}</p><div className="evidence">{Array.isArray(decision.evidence) && decision.evidence.map((item: { metric: string; value: number }) => <span key={item.metric}><small>{item.metric}</small><b>{item.metric.includes("fare") || item.metric.includes("median") ? inr.format(item.value) : `${item.value}%`}</b></span>)}</div><p className="disclaimer">{String(decision.disclaimer)}</p></div> : <Empty message="Enter a route and lead time to receive a calculated recommendation." />}</ChartPanel></div>; }

  function ScenarioView() { return <div className="dashboard-grid split-grid"><ChartPanel title="Scenario simulation" subtitle="What happens if a selected route’s core fare moves?"><form className="form" onSubmit={runScenario}><label>Route<select value={selectedRoute} onChange={e => setSelectedRoute(e.target.value)}>{meta?.routes.map(route => <option key={route}>{route}</option>)}</select></label><label>Fare movement (%)<input type="number" min="-80" max="300" value={scenarioChange} onChange={e => setScenarioChange(e.target.value)}/></label><button className="primary" type="submit"><SlidersHorizontal size={16}/> Run scenario</button></form></ChartPanel><ChartPanel title="Estimated index effect" subtitle="Before and after calculation">{scenario ? <div className="scenario"><div><span>Route index</span><b>{String(scenario.route_index_before)} → {String(scenario.route_index_after)}</b></div><div><span>National index</span><b>{String(scenario.national_index_before)} → {String(scenario.national_index_after)}</b></div><div><span>National impact</span><b className="positive">{signed(Number(scenario.national_index_impact_points))} points</b></div><p className="disclaimer">{String(scenario.disclaimer)}</p></div> : <Empty message="Run a hypothetical fare movement to calculate the prototype index impact." />}</ChartPanel></div>; }

  function QualityView() { return <div className="dashboard-grid split-grid"><ChartPanel title="Data Quality Monitor" subtitle="Observations are checked before index aggregation">{quality?.available ? <div className="quality-grid"><div><small>Quality score</small><b>{String(quality.average_quality_score)}%</b></div><div><small>Valid</small><b>{String(quality.valid)}</b></div><div><small>Invalid</small><b>{String(quality.invalid)}</b></div><div><small>Flagged outliers</small><b>{String(quality.outliers)}</b></div></div> : <Empty message={String(quality?.message)} />}</ChartPanel><ChartPanel title="Controls and treatment" subtitle="High values are not automatically removed"><ul className="method-list">{Array.isArray(quality?.checks) && quality.checks.map(check => <li key={check}>{check}</li>)}<li>{String(quality?.note || "")}</li></ul></ChartPanel></div>; }

  function MethodView() { return <div className="methodology"><ChartPanel title="AirIndex India — Methodology" subtitle="Prototype methodology and limitations"><div className="method-columns"><section><h3>Collection & processing</h3><p>Collectors are designed for authorized airline/OTA APIs, permitted sources or user-provided CSV. This V1 uses clearly marked deterministic development / replay data. No CAPTCHA, access-control, robots or rate-limit bypassing is implemented.</p><p>Core fare is normalized as base fare + taxes + mandatory fees. Optional extras are excluded. Required-field, total-consistency, duplicate and robust IQR/MAD checks are applied; flagged observations remain reviewable.</p><h3>Index construction</h3><p>Daily route mean core fares feed a transparent Laspeyres-style weighted relative price index with base period 100. Daily, weekly and monthly series are available from the same raw observations. Route contributions show each basket route’s movement in index points.</p></section><section><h3>Intelligence layer</h3><p>Market shocks compare route-level movements with robust historical thresholds. The explanation engine only describes measurable lead-time, availability and price evidence; it does not invent causal factors such as fuel costs.</p><p>The forecast is an explainable recent linear-trend baseline with an uncertainty indication. Traveller guidance and what-if results are decision support and scenario calculations, not guarantees.</p><h3>Limitations</h3><p className="disclaimer">This prototype is not an official CPI calculation and does not represent official Government of India weights or statistics.</p><p className="disclaimer">{meta?.source_note}</p></section></div></ChartPanel></div>; }

  let content: React.ReactNode = <Dashboard />;
  if (summary.available) {
    if (view === "index") content = <IndexView />; else if (view === "routes") content = <RoutesView />; else if (view === "airlines") content = <AirlinesView />; else if (view === "lead") content = <LeadView />; else if (view === "shocks") content = <ShocksView />; else if (view === "forecast") content = <ForecastView />; else if (view === "traveller") content = <TravellerView />; else if (view === "scenario") content = <ScenarioView />; else if (view === "quality") content = <QualityView />; else if (view === "method") content = <MethodView />;
  }

  return <div className="app-shell"><aside className="sidebar"><div className="brand"><span className="brand-mark"><Activity size={22}/></span><div><strong>AIRINDEX</strong><small>INDIA</small></div></div><div className="prototype-pill">SIH26056 · PROTOTYPE</div><nav>{nav.map(item => { const Icon = item.icon; return <button key={item.id} onClick={() => setView(item.id)} className={view === item.id ? "active" : ""}><Icon size={17}/><span>{item.label}</span><ChevronRight size={14}/></button>; })}</nav><div className="sidebar-footer"><span className="status-light"/> Development / replay data<br/><small>Not live airline pricing</small></div></aside><main><header className="topbar"><div><p className="eyebrow">REAL-TIME AIRFARE INTELLIGENCE</p><h1>{nav.find(item => item.id === view)?.label}</h1></div><div className="top-actions"><button className="outline" onClick={load} disabled={loading}><RefreshCw size={16} className={loading ? "spin" : ""}/> Refresh</button><button className="primary" onClick={initialize} disabled={initializing}>{initializing ? <LoaderCircle className="spin" size={16}/> : <Database size={16}/>} {initializing ? "Initializing…" : summary.available ? "Dataset Ready" : "Initialize Dataset"}</button></div></header><div className="data-banner"><span><span className="status-light"/> {summary.source || "Awaiting development / replay data"}</span><span>{summary.last_updated ? `Last calculated ${new Date(summary.last_updated).toLocaleString("en-IN")}` : "Connect the local API to begin"}</span></div>{error && <div className="error"><AlertTriangle size={17}/><span>{error}</span></div>}{loading ? <div className="loading"><LoaderCircle className="spin" size={26}/><p>Loading calculated intelligence…</p></div> : <div className="content">{content}</div>}</main></div>;
}

export default App;
