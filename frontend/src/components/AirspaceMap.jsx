function Aircraft({ x, y, label, highlighted = false }) {
  return (
    <g className={highlighted ? "aircraft highlighted" : "aircraft"}>
      <circle cx={x} cy={y} r="4" />
      <circle cx={x} cy={y} r="9" className="aircraft-halo" />
      {label && (
        <text x={x + 10} y={y - 8} className="aircraft-label">
          {label}
        </text>
      )}
    </g>
  );
}

export default function AirspaceMap({
  selectedCandidate,
  targetFlightId,
}) {
  const routeMap = {
    "ALT-B": "route-b",
    "ALT-C": "route-c",
    "ALT-D": "route-d",
  };

  const routeClass = routeMap[selectedCandidate?.id] || "route-d";

  return (
    <section className="panel map-panel">
      <div className="panel-heading map-heading">
        <div>
          <span className="eyebrow">NETWORK VIEW</span>
          <h2>Airspace impact simulation</h2>
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
              <feGaussianBlur stdDeviation="4" result="blur" />
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

          <text x="32" y="42" className="map-label">
            SCHEMATIC AIRSPACE
          </text>

          <text x="32" y="64" className="map-sub-label">
            SIMULATED / DETERMINISTIC STATE
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

          <text x="215" y="255" className="sector-label">
            S3
          </text>

          <text x="445" y="245" className="sector-label stressed">
            S4 · 92%
          </text>

          <text x="690" y="255" className="sector-label critical">
            S5 · 90%
          </text>

          <path
            d="M585 95 C680 105 755 165 790 250 C820 320 780 380 690 398"
            className="weather-cell"
          />

          <text x="675" y="125" className="weather-label">
            WX-BOM-01
          </text>

          <text x="675" y="145" className="weather-label-small">
            SEVERE · +20%
          </text>

          <line
            x1="100"
            y1="252"
            x2="805"
            y2="252"
            className="reference-line"
          />

          <g className={`candidate-route ${routeClass}`}>
            <path
              d="M115 252 C250 210 320 185 430 220 C565 265 655 255 790 300"
            />
          </g>

          <g className="route-origin">
            <circle cx="105" cy="252" r="11" />
            <text x="105" y="286" textAnchor="middle">
              DEL
            </text>
          </g>

          <g className="route-destination">
            <circle cx="800" cy="300" r="11" />
            <text x="800" y="335" textAnchor="middle">
              BOM
            </text>
          </g>

          <Aircraft x={145} y={220} label="F081" />
          <Aircraft x={230} y={330} label="F207" />
          <Aircraft x={350} y={155} label="F143" />
          <Aircraft
            x={470}
            y={210}
            label={targetFlightId}
            highlighted
          />
          <Aircraft x={585} y={310} label="F099" />
          <Aircraft x={685} y={190} label="F311" />
          <Aircraft x={755} y={350} label="F186" />

          <circle cx="470" cy="210" r="24" className="target-ring" />

          <text x="470" y="178" textAnchor="middle" className="target-label">
            TARGET
          </text>

          <g className="capacity-warning">
            <rect x="575" y="445" width="245" height="32" rx="7" />
            <circle cx="594" cy="461" r="4" />
            <text x="607" y="466">
              S5 nearing capacity threshold
            </text>
          </g>
        </svg>
      </div>
    </section>
  );
}