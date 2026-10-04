function MetricCard({
  label,
  value,
  subvalue,
  tone = "",
}) {
  return (
    <div className={`metric-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{subvalue}</small>
    </div>
  );
}

export default function MetricsPanel({
  network,
  selectedCandidate,
}) {
  const utilizationPct = Math.round(
    selectedCandidate.peakSectorUtilization * 100
  );

  return (
    <section className="panel metrics-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">NETWORK KPIs</span>
          <h2>Ripple impact</h2>
        </div>

        <span className="live-indicator">
          <i />
          SIMULATION
        </span>
      </div>

      <div className="metrics-grid">
        <MetricCard
          label="Active aircraft"
          value={network.activeAircraft}
          subvalue="Tracked"
        />

        <MetricCard
          label="Holding"
          value={network.aircraftInHolding}
          subvalue="Aircraft"
          tone="warning"
        />

        <MetricCard
          label="Stressed sectors"
          value={network.stressedSectors}
          subvalue="Current"
          tone="warning"
        />

        <MetricCard
          label="Network delay"
          value={`+${network.networkDelayMin}m`}
          subvalue="Baseline"
          tone="negative"
        />

        <MetricCard
          label="Peak utilization"
          value={`${utilizationPct}%`}
          subvalue={selectedCandidate.id}
        />

        <MetricCard
          label="Network delta"
          value={`${selectedCandidate.networkDelayDeltaMin > 0 ? "+" : ""}${selectedCandidate.networkDelayDeltaMin}m`}
          subvalue="Candidate impact"
          tone={
            selectedCandidate.networkDelayDeltaMin <= 0
              ? "positive"
              : "negative"
          }
        />
      </div>
    </section>
  );
}