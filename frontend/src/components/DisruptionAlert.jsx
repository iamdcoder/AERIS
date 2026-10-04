function extractResourceId(
  alert,
) {
  const text = String(
    alert?.summary ||
      "",
  ).toUpperCase();

  const match =
    text.match(
      /\b(?:WX|R)-[A-Z0-9_-]+\b/,
    );

  return (
    match?.[0] ||
    alert?.resource_id ||
    alert?.weather_cell_id ||
    alert?.restriction_id ||
    null
  );
}


function alertKey(
  alert,
) {
  const type =
    String(
      alert?.type ||
        "ALERT",
    )
      .replaceAll(
        "_",
        " ",
      )
      .toUpperCase();

  const resource =
    extractResourceId(
      alert,
    );

  if (resource) {
    return `${type}|${resource}`;
  }

  return `${type}|${String(
    alert?.summary ||
      "",
  ).trim()}`;
}


function uniqueAlerts(
  alerts,
) {
  const seen =
    new Set();

  return (
    Array.isArray(
      alerts,
    )
      ? alerts
      : []
  ).filter(
    (alert) => {
      const key =
        alertKey(
          alert,
        );

      if (
        seen.has(key)
      ) {
        return false;
      }

      seen.add(
        key,
      );

      return true;
    },
  );
}


function readableType(
  type,
) {
  return String(
    type ||
      "ALERT",
  )
    .replaceAll(
      "_",
      " ",
    )
    .replaceAll(
      "-",
      " ",
    )
    .toUpperCase();
}


export default function DisruptionAlert({
  disruption,
}) {
  const alerts =
    uniqueAlerts(
      disruption?.alerts,
    );


  return (
    <section className="panel disruption-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">
            ACTIVE DISRUPTION
          </span>

          <h2>
            {disruption?.title ||
              "Active airspace disruption"}
          </h2>
        </div>

        <span className="severity-badge high">
          {String(
            disruption?.severity ||
              "HIGH",
          ).toUpperCase()}
        </span>
      </div>


      <p className="panel-description">
        {disruption?.summary ||
          "AERIS is reading the current deterministic airspace state."}
      </p>


      <div className="alert-stack">
        {alerts.length ===
        0 ? (
          <div className="alert-row">
            <span className="alert-dot" />

            <div>
              <strong>
                NO ACTIVE ALERT
              </strong>

              <span>
                No additional operational disruption signals are currently reported.
              </span>
            </div>
          </div>
        ) : (
          alerts.map(
            (
              alert,
            ) => (
              <div
                className="alert-row"
                key={alertKey(
                  alert,
                )}
              >
                <span className="alert-dot" />

                <div>
                  <strong>
                    {readableType(
                      alert.type,
                    )}
                  </strong>

                  <span>
                    {
                      alert.summary
                    }
                  </span>
                </div>
              </div>
            ),
          )
        )}
      </div>
    </section>
  );
}