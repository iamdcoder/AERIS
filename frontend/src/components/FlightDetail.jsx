function Stat({ label, value, subvalue }) {
  return (
    <div className="flight-stat">
      <span>{label}</span>
      <strong>{value}</strong>
      {subvalue && <small>{subvalue}</small>}
    </div>
  );
}

export default function FlightDetail({ flight }) {
  const fuelMargin = flight.fuelRemainingMin - flight.reserveRequiredMin;

  return (
    <section className="panel flight-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">TARGET FLIGHT</span>
          <h2>
            {flight.callsign}
            <span className="muted-id"> / {flight.id}</span>
          </h2>
        </div>

        <span className="status-badge degraded">{flight.status}</span>
      </div>

      <div className="flight-route">
        <div className="airport-code">
          <strong>{flight.origin}</strong>
          <span>ORIGIN</span>
        </div>

        <div className="route-arrow">
          <span />
          <b>→</b>
          <span />
        </div>

        <div className="airport-code destination">
          <strong>{flight.destination}</strong>
          <span>DESTINATION</span>
        </div>
      </div>

      <div className="flight-stats">
        <Stat
          label="Fuel remaining"
          value={`${flight.fuelRemainingMin} min`}
          subvalue={`Reserve ${flight.reserveRequiredMin} min`}
        />

        <Stat
          label="Safety margin"
          value={`${fuelMargin} min`}
          subvalue="Above reserve"
        />

        <Stat
          label="Current delay"
          value={`+${flight.currentDelayMin} min`}
          subvalue={flight.performanceClass}
        />
      </div>
    </section>
  );
}