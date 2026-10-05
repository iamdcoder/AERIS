function Aircraft({
  x,
  y,
  label,
  highlighted = false,
}) {
  return (
    <g
      className={
        highlighted
          ? "aircraft highlighted"
          : "aircraft"
      }
    >
      <circle
        cx={x}
        cy={y}
        r="4"
      />

      <circle
        cx={x}
        cy={y}
        r="9"
        className="aircraft-halo"
      />

      {label && (
        <text
          x={x + 10}
          y={y - 8}
          className="aircraft-label"
        >
          {label}
        </text>
      )}
    </g>
  );
}


function sectorUtilization(
  sector,
) {
  const direct =
    Number(
      sector?.utilization_pct ??
        sector?.projected_utilization,
    );

  const forecast =
    Number(
      sector?.forecast_traffic,
    );

  const capacity =
    Number(
      sector?.capacity,
    );

  const directRatio =
    Number.isFinite(
      direct,
    )
      ? direct <= 2
        ? direct
        : direct / 100
      : null;

  const forecastRatio =
    Number.isFinite(
      forecast,
    ) &&
    Number.isFinite(
      capacity,
    ) &&
    capacity > 0
      ? forecast /
        capacity
      : null;

  if (
    directRatio ===
      null &&
    forecastRatio ===
      null
  ) {
    return 0;
  }

  if (
    directRatio ===
    null
  ) {
    return forecastRatio;
  }

  if (
    forecastRatio ===
    null
  ) {
    return directRatio;
  }

  return Math.max(
    directRatio,
    forecastRatio,
  );
}


function isStressed(
  sector,
) {
  const status =
    String(
      sector?.status ||
        "",
    ).toUpperCase();

  return (
    [
      "STRESSED",
      "CONGESTED",
      "OVERLOADED",
      "CRITICAL",
    ].includes(
      status,
    ) ||
    sectorUtilization(
      sector,
    ) >= 0.85
  );
}


export default function AirspaceMap({
  selectedCandidate,
  targetFlightId,
  sectors = [],
  weather = [],
}) {
  const routeClass =
    selectedCandidate?.id ===
    "ALT-B"
      ? "route-b"
      : selectedCandidate?.id ===
          "ALT-C"
        ? "route-c"
        : "route-d";

  const rankedSectors =
    [
      ...sectors,
    ].sort(
      (a, b) =>
        sectorUtilization(
          b,
        ) -
        sectorUtilization(
          a,
        ),
    );

  const primarySector =
    rankedSectors[0] ||
    {};

  const secondarySector =
    rankedSectors[1] ||
    {};

  const tertiarySector =
    rankedSectors[2] ||
    {};

  const weatherCell =
    weather[0] ||
    {};

  const stressedCount =
    sectors.filter(
      isStressed,
    ).length;

  return (
    <section className="panel map-panel">
      <div className="panel-heading map-heading">
        <div>
          <span className="eyebrow">
            NETWORK VIEW
          </span>

          <h2>
            Airspace impact simulation
          </h2>
        </div>

        <div className="map-legend">
          <span>
            <i className="legend-dot aircraft-dot" />
            Aircraft
          </span>

          <span>
            <i className="legend-dot weather-dot" />
            Weather
          </span>

          <span>
            <i className="legend-dot route-dot" />
            Candidate
          </span>
        </div>
      </div>

      <div className="map-stage">
        <svg
          viewBox="0 0 900 500"
          className="airspace-svg"
          role="img"
          aria-label="Schematic airspace simulation"
        >
          <defs>
            <pattern
              id="grid"
              width="45"
              height="45"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 45 0 L 0 0 0 45"
                fill="none"
                stroke="currentColor"
                strokeOpacity="0.08"
                strokeWidth="1"
              />
            </pattern>

            <filter id="glow">
              <feGaussianBlur
                stdDeviation="4"
                result="blur"
              />

              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          <rect
            width="900"
            height="500"
            className="map-background"
          />

          <rect
            width="900"
            height="500"
            fill="url(#grid)"
          />

          <text
            x="32"
            y="42"
            className="map-label"
          >
            SCHEMATIC AIRSPACE
          </text>

          <text
            x="32"
            y="64"
            className="map-sub-label"
          >
            LIVE DETERMINISTIC ENGINE STATE
          </text>

          <polygon
            points="100,110 330,90 430,225 350,410 120,380"
            className="sector sector-normal"
          />

          <polygon
            points="330,90 555,80 625,225 520,365 350,410 430,225"
            className="sector sector-stressed"
          />

          <polygon
            points="555,80 805,130 830,355 650,420 520,365 625,225"
            className="sector sector-critical"
          />

          <text
            x="205"
            y="255"
            className="sector-label"
          >
            {primarySector.id ||
              "S3"}
            {" · "}
            {Math.round(
              sectorUtilization(
                primarySector,
              ) *
                100,
            )}
            %
          </text>

          <text
            x="445"
            y="245"
            className="sector-label stressed"
          >
            {secondarySector.id ||
              "S4"}
            {" · "}
            {Math.round(
              sectorUtilization(
                secondarySector,
              ) *
                100,
            )}
            %
          </text>

          <text
            x="690"
            y="255"
            className="sector-label critical"
          >
            {tertiarySector.id ||
              "S5"}
            {" · "}
            {Math.round(
              sectorUtilization(
                tertiarySector,
              ) *
                100,
            )}
            %
          </text>

          <polygon
            points="590,90 700,102 795,175 815,270 765,350 670,365 603,295 580,210"
            fill="rgba(255, 115, 115, 0.09)"
            stroke="rgba(255, 115, 115, 0.48)"
            strokeWidth="2"
            strokeDasharray="10 8"
          />

          <text
            x="650"
            y="122"
            className="weather-label"
          >
            {weatherCell.id ||
              "WEATHER"}
          </text>

          <text
            x="650"
            y="142"
            className="weather-label-small"
          >
            {String(
              weatherCell.intensity ||
                weatherCell.severity ||
                "ACTIVE",
            ).toUpperCase()}
          </text>

          <line
            x1="100"
            y1="252"
            x2="805"
            y2="252"
            className="reference-line"
          />

          <g
            className={`candidate-route ${routeClass}`}
          >
            <path d="M115 252 C250 210 320 185 430 220 C565 265 655 255 790 300" />
          </g>

          <g className="route-origin">
            <circle
              cx="105"
              cy="252"
              r="11"
            />

            <text
              x="105"
              y="286"
              textAnchor="middle"
            >
              DEL
            </text>
          </g>

          <g className="route-destination">
            <circle
              cx="800"
              cy="300"
              r="11"
            />

            <text
              x="800"
              y="335"
              textAnchor="middle"
            >
              BOM
            </text>
          </g>

          <Aircraft
            x={145}
            y={220}
            label="AI081"
          />

          <Aircraft
            x={230}
            y={330}
            label="AI207"
          />

          <Aircraft
            x={350}
            y={155}
            label="AI143"
          />

          <Aircraft
            x={470}
            y={210}
            label={
              targetFlightId ||
              "F102"
            }
            highlighted
          />

          <Aircraft
            x={585}
            y={310}
            label="AI099"
          />

          <Aircraft
            x={685}
            y={190}
            label="AI311"
          />

          <Aircraft
            x={755}
            y={350}
            label="AI186"
          />

          <circle
            cx="470"
            cy="210"
            r="24"
            className="target-ring"
          />

          <text
            x="470"
            y="178"
            textAnchor="middle"
            className="target-label"
          >
            TARGET
          </text>

          <g className="capacity-warning">
            <rect
              x="575"
              y="445"
              width="245"
              height="32"
              rx="7"
            />

            <circle
              cx="594"
              cy="461"
              r="4"
            />

            <text
              x="607"
              y="466"
            >
              Network pressure
              {" · "}
              {stressedCount}
              {" "}
              stressed
              {" "}
              sector(s)
            </text>
          </g>
        </svg>
      </div>
    </section>
  );
}