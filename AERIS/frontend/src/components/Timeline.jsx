export default function Timeline({
  items,
  simulationTimeMin,
}) {
  return (
    <section className="panel timeline-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">SCENARIO CLOCK</span>
          <h2>Disruption progression</h2>
        </div>

        <span className="simulation-clock">
          T+{String(simulationTimeMin).padStart(2, "0")}
        </span>
      </div>

      <div className="timeline">
        {items.map((item, index) => {
          const current = item.time === `T+${String(simulationTimeMin).padStart(2, "0")}`;

          return (
            <div
              className={`timeline-item ${
                current ? "current" : ""
              }`}
              key={`${item.time}-${index}`}
            >
              <div className="timeline-dot" />

              <div className="timeline-content">
                <span>{item.time}</span>
                <strong>{item.title}</strong>
                <p>{item.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}