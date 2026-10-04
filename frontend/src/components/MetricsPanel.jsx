function MetricCard({
  label,
  value,
  subvalue,
  tone = "",
}) {
  return (
    <div
      className={`metric-card ${tone}`}
    >
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

      <small>
        {subvalue}
      </small>
    </div>
  );
}


function formatMinutes(
  value,
  prefix = "",
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  const number =
    Number(value);

  if (
    !Number.isFinite(
      number,
    )
  ) {
    return "—";
  }

  return `${prefix}${number.toFixed(
    2,
  )}m`;
}


function formatPercent(
  value,
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  const number =
    Number(value);

  if (
    !Number.isFinite(
      number,
    )
  ) {
    return "—";
  }

  const ratio =
    number > 2
      ? number / 100
      : number;

  return `${Math.round(
    ratio * 100,
  )}%`;
}


export default function MetricsPanel({
  network,
  selectedCandidate,
}) {
  const projectedPeak =
    selectedCandidate
      ?.peakSectorUtilization;

  const networkDelta =
    selectedCandidate
      ?.networkDelayDeltaMin;

  return (
    <section className="panel metrics-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">
            NETWORK KPIs
          </span>

          <h2>
            Ripple impact
          </h2>
        </div>

        <span className="live-indicator">
          <i />
          DETERMINISTIC
        </span>
      </div>


      <div className="metrics-grid">
        <MetricCard
          label="Active aircraft"
          value={
            network?.activeAircraft ??
            "—"
          }
          subvalue="Current tracked"
        />


        <MetricCard
          label="Holding"
          value={
            network?.aircraftInHolding ??
            "—"
          }
          subvalue="Current aircraft"
          tone="warning"
        />


        <MetricCard
          label="Stressed sectors"
          value={
            network?.stressedSectors ??
            "—"
          }
          subvalue="Current state"
          tone="warning"
        />


        <MetricCard
          label="Current network delay"
          value={
            formatMinutes(
              network?.networkDelayMin,
              network?.networkDelayMin >
                0
                ? "+"
                : "",
            )
          }
          subvalue="Current total"
          tone="negative"
        />


        <MetricCard
          label="Projected peak"
          value={
            formatPercent(
              projectedPeak,
            )
          }
          subvalue={
            selectedCandidate?.id
              ? `${selectedCandidate.id} candidate`
              : "No candidate selected"
          }
        />


        <MetricCard
          label="Network delta"
          value={
            formatMinutes(
              networkDelta,
              networkDelta >
                0
                ? "+"
                : "",
            )
          }
          subvalue="Selected candidate impact"
          tone={
            networkDelta ===
              null ||
            networkDelta ===
              undefined
              ? ""
              : networkDelta <=
                  0
                ? "positive"
                : "negative"
          }
        />
      </div>
    </section>
  );
}