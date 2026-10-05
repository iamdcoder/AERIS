import React from "react";

function formatEventTime(event) {
  const value = event?.occurred_at;
  if (!value) return "--:--:--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--:--:--";
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function labelForEvent(event) {
  const payload = event?.payload || {};
  if (payload.title) return payload.title;
  const sourceEvent = payload.source_event;
  if (sourceEvent) {
    return sourceEvent
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }
  return event?.event_type || "Operational update";
}

function detailForEvent(event) {
  const payload = event?.payload || {};

  if (payload.message) return payload.message;

  switch (event?.event_type) {
    case "WEATHER_UPDATE":
      return `Weather cell ${event.entity_id} is ${payload.intensity || "changing"} near the operating corridor.`;
    case "SECTOR_CAPACITY_UPDATE":
      return `Sector ${event.entity_id} capacity updated to ${payload.capacity || "new"} flights.`;
    case "AIRPORT_CAPACITY_UPDATE":
      return `Airport ${event.entity_id} arrival capacity updated.`;
    case "FLIGHT_STATE_UPDATE":
    case "SURVEILLANCE_UPDATE":
      return `${event.entity_id} is ${payload.status || "operating"}; fuel and trajectory state updated.`;
    case "TRAFFIC_UPDATE":
      return "Network traffic/holding conditions changed.";
    case "RESTRICTION_UPDATE":
      return `Restriction ${event.entity_id} changed routing conditions.`;
    default:
      return "Operational conditions changed.";
  }
}

export default function LiveOperationsPanel({
  snapshot,
  connected,
  transport,
  onStart,
  onStop,
  onReset,
  onReassess,
  canReassess,
  busy,
}) {
  const events = snapshot?.recent_events || [];
  const importantEvents =
    events.filter(
      (event) =>
        event?.event_type !== "SURVEILLANCE_UPDATE",
    );
  const displayEvents =
    importantEvents.length
      ? importantEvents.slice(0, 8)
      : events.slice(0, 8);
  const simulationTime =
    snapshot?.last_simulation_time_min ?? 0;
  const running = Boolean(snapshot?.running);
  const done = Boolean(snapshot?.done);

  return (
    <section className="panel live-operations-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">
            OPERATIONAL DATA FEED
          </span>
          <h2>Live airspace conditions</h2>
          <p className="panel-description">
            Deterministic replay of normalized airline, weather,
            airport and airspace events. Production adapters can
            later publish the same event contract.
          </p>
        </div>

        <div className="live-feed-status">
          <span
            className={
              connected
                ? "live-dot connected"
                : "live-dot"
            }
          />
          {connected
            ? `FEED ${transport}`
            : "FEED OFFLINE"}
        </div>
      </div>

      <div className="live-feed-toolbar">
        <div className="live-feed-clock">
          <span>SIMULATION CLOCK</span>
          <strong>
            T+
            {String(simulationTime).padStart(2, "0")}
          </strong>
        </div>

        <div className="live-feed-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={onReset}
            disabled={busy}
          >
            RESET FEED
          </button>

          {canReassess && (
            <button
              type="button"
              className="warning-button"
              onClick={onReassess}
              disabled={busy}
            >
              REASSESS CURRENT CONDITIONS
            </button>
          )}

          {running ? (
            <button
              type="button"
              className="run-button"
              onClick={onStop}
              disabled={busy}
            >
              STOP LIVE FEED
            </button>
          ) : (
            <button
              type="button"
              className="run-button"
              onClick={onStart}
              disabled={busy || done}
            >
              {done ? "REPLAY COMPLETE" : "START LIVE FEED"}
            </button>
          )}
        </div>
      </div>

      <div className="live-feed-grid">
        {displayEvents.length ? (
          displayEvents.map((event) => (
            <article
              className={`live-event ${String(
                event.severity || "INFO",
              ).toLowerCase()}`}
              key={event.event_id}
            >
              <div className="live-event-time">
                T+
                {String(
                  event.simulation_time_min ?? 0,
                ).padStart(2, "0")}
                <span>{formatEventTime(event)}</span>
              </div>

              <div className="live-event-body">
                <strong>{labelForEvent(event)}</strong>
                <p>{detailForEvent(event)}</p>
              </div>

              <div className="live-event-source">
                {event.entity_type} · {event.entity_id}
              </div>
            </article>
          ))
        ) : (
          <div className="live-feed-empty">
            Start the live feed to watch operational events arrive
            and move the deterministic airspace state forward.
          </div>
        )}
      </div>
    </section>
  );
}
