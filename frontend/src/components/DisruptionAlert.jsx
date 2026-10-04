export default function DisruptionAlert({ disruption }) {
  return (
    <section className="panel disruption-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">ACTIVE DISRUPTION</span>
          <h2>{disruption.title}</h2>
        </div>

        <span className="severity-badge high">HIGH</span>
      </div>

      <p className="panel-description">{disruption.summary}</p>

      <div className="alert-stack">
        {disruption.alerts.map((alert) => (
          <div className="alert-row" key={alert.type}>
            <span className="alert-dot" />
            <div>
              <strong>{alert.type.replaceAll("_", " ")}</strong>
              <span>{alert.summary}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}