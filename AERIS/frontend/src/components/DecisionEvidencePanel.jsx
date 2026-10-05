function formatNumber(
  value,
  digits = 2,
) {
  const number =
    Number(value);

  if (
    !Number.isFinite(
      number,
    )
  ) {
    return "—";
  }

  return number.toFixed(
    digits,
  );
}


function formatSigned(
  value,
  digits = 2,
) {
  const number =
    Number(value);

  if (
    !Number.isFinite(
      number,
    )
  ) {
    return "—";
  }

  return `${
    number > 0
      ? "+"
      : ""
  }${number.toFixed(
    digits,
  )}`;
}


function formatPercent(
  value,
) {
  const number =
    Number(value);

  if (
    !Number.isFinite(
      number,
    )
  ) {
    return "—";
  }

  return `${Math.round(
    number * 100,
  )}%`;
}


function MetricBlock({
  label,
  value,
  caption,
  emphasis,
}) {
  return (
    <div
      style={{
        padding:
          "13px 14px",
        border:
          "1px solid var(--border)",
        borderRadius:
          "8px",
        background:
          "rgba(8, 22, 37, 0.72)",
      }}
    >
      <span
        style={{
          display:
            "block",
          color:
            "var(--muted-2)",
          fontSize:
            "8px",
          textTransform:
            "uppercase",
          letterSpacing:
            "0.08em",
        }}
      >
        {label}
      </span>

      <strong
        style={{
          display:
            "block",
          marginTop:
            "6px",
          fontSize:
            "17px",
          color:
            emphasis ||
            "#deedfa",
        }}
      >
        {value}
      </strong>

      <small
        style={{
          display:
            "block",
          marginTop:
            "4px",
          color:
            "var(--muted-2)",
          fontSize:
            "9px",
          lineHeight:
            "1.4",
        }}
      >
        {caption}
      </small>
    </div>
  );
}


export default function DecisionEvidencePanel({
  candidates = [],
  agentState,
}) {
  const recommendation =
    agentState?.recommendation ||
    null;

  const recommendedId =
    recommendation?.candidate_id ||
    null;

  const recommended =
    candidates.find(
      (candidate) =>
        candidate.id ===
        recommendedId,
    ) ||
    candidates.find(
      (candidate) =>
        candidate.feasible &&
        !candidate.operatorRejected,
    ) ||
    null;


  const operationalCandidates =
    candidates.filter(
      (candidate) =>
        candidate.feasible &&
        !candidate.operatorRejected,
    );


  const localLeader =
    operationalCandidates
      .filter(
        (candidate) =>
          candidate.localScore !==
            null &&
          candidate.localScore !==
            undefined,
      )
      .sort(
        (
          first,
          second,
        ) =>
          Number(
            second.localScore,
          ) -
          Number(
            first.localScore,
          ),
      )[0] ||
    null;


  const isFlip =
    Boolean(
      localLeader &&
        recommended &&
        localLeader.id !==
          recommended.id,
    );


  const networkImprovement =
    localLeader &&
    recommended &&
    localLeader.networkDelayDeltaMin !==
      null &&
    recommended.networkDelayDeltaMin !==
      null
      ? Number(
          localLeader.networkDelayDeltaMin,
        ) -
        Number(
          recommended.networkDelayDeltaMin,
        )
      : null;


  const resilienceGain =
    localLeader &&
    recommended &&
    localLeader.resilience !==
      null &&
    recommended.resilience !==
      null
      ? Number(
          recommended.resilience,
        ) -
        Number(
          localLeader.resilience,
        )
      : null;


  const recommendedStress =
    recommended?.stressTotal
      ? `${recommended.stressSurvival}/${recommended.stressTotal}`
      : "—";


  const localStress =
    localLeader?.stressTotal
      ? `${localLeader.stressSurvival}/${localLeader.stressTotal}`
      : "—";


  const whySelected =
    Array.isArray(
      recommendation?.why_selected,
    )
      ? recommendation.why_selected
      : [];


  const feasibleCount =
    operationalCandidates.length;


  const infeasibleCount =
    candidates.filter(
      (candidate) =>
        !candidate.feasible,
    ).length;


  if (
    !recommended
  ) {
    return (
      <section className="panel decision-evidence-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">
              DECISION BASIS
            </span>

            <h2>
              Why AERIS recommends
            </h2>
          </div>
        </div>

        <div
          className="simulation-notice"
          style={{
            marginBottom:
              "20px",
          }}
        >
          Decision evidence will appear after AERIS completes candidate evaluation.
        </div>
      </section>
    );
  }


  return (
    <section className="panel decision-evidence-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">
            DECISION BASIS
          </span>

          <h2>
            Why AERIS recommends{" "}
            {recommended.id}
          </h2>
        </div>

        <span
          className="privacy-badge"
        >
          DETERMINISTIC EVIDENCE
        </span>
      </div>


      <div
        style={{
          padding:
            "16px 20px 4px",
        }}
      >
        <div
          style={{
            display:
              "grid",
            gridTemplateColumns:
              "repeat(4, 1fr)",
            gap:
              "10px",
          }}
        >
          <MetricBlock
            label="Network delta"
            value={
              recommended.networkDelayDeltaMin ===
              null
                ? "—"
                : `${formatSigned(
                    recommended.networkDelayDeltaMin,
                  )} min`
            }
            caption="Predicted network delay change"
            emphasis={
              recommended.networkDelayDeltaMin <=
              0
                ? "var(--good)"
                : "var(--danger)"
            }
          />


          <MetricBlock
            label="Resilience"
            value={formatNumber(
              recommended.resilience,
            )}
            caption="Network resilience score"
            emphasis="var(--good)"
          />


          <MetricBlock
            label="Stress survival"
            value={
              recommendedStress
            }
            caption="Future scenarios survived"
            emphasis={
              recommended.stressSurvival >=
              4
                ? "var(--good)"
                : "var(--warning)"
            }
          />


          <MetricBlock
            label="Feasible set"
            value={`${feasibleCount}/${candidates.length}`}
            caption={`${infeasibleCount} candidate(s) failed hard constraints`}
          />
        </div>
      </div>


      {isFlip && (
        <div
          style={{
            margin:
              "16px 20px",
            padding:
              "14px 15px",
            border:
              "1px solid rgba(84, 214, 255, 0.22)",
            borderRadius:
              "8px",
            background:
              "rgba(84, 214, 255, 0.055)",
          }}
        >
          <div
            style={{
              display:
                "flex",
              justifyContent:
                "space-between",
              alignItems:
                "center",
              gap:
                "16px",
              marginBottom:
                "9px",
            }}
          >
            <strong
              style={{
                color:
                  "var(--accent)",
                fontSize:
                  "11px",
                letterSpacing:
                  "0.06em",
              }}
            >
              LOCAL VS NETWORK WINNER
            </strong>

            <span
              className="privacy-badge"
            >
              DECISION FLIP
            </span>
          </div>


          <p
            style={{
              margin:
                "0",
              color:
                "#9bb0c5",
              fontSize:
                "10px",
              lineHeight:
                "1.55",
            }}
          >
            {localLeader.id} was the
            locally strongest feasible
            option, but AERIS selected{" "}
            <strong
              style={{
                color:
                  "var(--accent)",
              }}
            >
              {recommended.id}
            </strong>{" "}
            because its predicted network
            outcome and future resilience
            were stronger.
          </p>


          <div
            style={{
              display:
                "grid",
              gridTemplateColumns:
                "1fr 1fr",
              gap:
                "10px",
              marginTop:
                "12px",
            }}
          >
            <div
              style={{
                padding:
                  "11px",
                border:
                  "1px solid var(--border)",
                borderRadius:
                  "7px",
                background:
                  "rgba(8, 22, 37, 0.65)",
              }}
            >
              <span
                style={{
                  display:
                    "block",
                  color:
                    "var(--muted-2)",
                  fontSize:
                    "8px",
                  textTransform:
                    "uppercase",
                }}
              >
                Local leader
              </span>

              <strong
                style={{
                  display:
                    "block",
                  marginTop:
                    "5px",
                  fontSize:
                    "14px",
                }}
              >
                {localLeader.id}
              </strong>

              <span
                style={{
                  display:
                    "block",
                  marginTop:
                    "5px",
                  color:
                    "var(--muted)",
                  fontSize:
                    "9px",
                }}
              >
                Local score{" "}
                {formatNumber(
                  localLeader.localScore,
                )}
                {" · "}
                Network{" "}
                {formatSigned(
                  localLeader.networkDelayDeltaMin,
                )}
                {" min"}
              </span>
            </div>


            <div
              style={{
                padding:
                  "11px",
                border:
                  "1px solid rgba(86, 221, 161, 0.18)",
                borderRadius:
                  "7px",
                background:
                  "rgba(86, 221, 161, 0.045)",
              }}
            >
              <span
                style={{
                  display:
                    "block",
                  color:
                    "var(--muted-2)",
                  fontSize:
                    "8px",
                  textTransform:
                    "uppercase",
                }}
              >
                Network winner
              </span>

              <strong
                style={{
                  display:
                    "block",
                  marginTop:
                    "5px",
                  color:
                    "var(--good)",
                  fontSize:
                    "14px",
                }}
              >
                {recommended.id}
              </strong>

              <span
                style={{
                  display:
                    "block",
                  marginTop:
                    "5px",
                  color:
                    "var(--muted)",
                  fontSize:
                    "9px",
                }}
              >
                Resilience{" "}
                {formatNumber(
                  recommended.resilience,
                )}
                {" · "}
                Stress{" "}
                {recommendedStress}
              </span>
            </div>
          </div>
        </div>
      )}


      <div
        style={{
          padding:
            "4px 20px 16px",
        }}
      >
        <span
          className="eyebrow"
        >
          QUANTIFIED TRADE-OFF
        </span>

        <div
          style={{
            display:
              "grid",
            gridTemplateColumns:
              "repeat(3, 1fr)",
            gap:
              "10px",
            marginTop:
              "10px",
          }}
        >
          <MetricBlock
            label="Network improvement"
            value={
              networkImprovement ===
                null
                ? "—"
                : `${formatNumber(
                    networkImprovement,
                  )} min`
            }
            caption={
              localLeader &&
              recommended
                ? `${localLeader.id} → ${recommended.id}`
                : "Compared with local leader"
            }
            emphasis={
              networkImprovement !==
                null &&
              networkImprovement >
                0
                ? "var(--good)"
                : "#deedfa"
            }
          />


          <MetricBlock
            label="Resilience gain"
            value={
              resilienceGain ===
                null
                ? "—"
                : `+${formatPercent(
                    resilienceGain,
                  )}`
            }
            caption="Compared with the local leader"
            emphasis="var(--good)"
          />


          <MetricBlock
            label="Stress comparison"
            value={`${localStress} → ${recommendedStress}`}
            caption="Local leader → recommended candidate"
            emphasis="var(--good)"
          />
        </div>
      </div>


      <div
        style={{
          borderTop:
            "1px solid var(--border)",
          padding:
            "16px 20px 20px",
        }}
      >
        <span
          className="eyebrow"
        >
          SELECTION EVIDENCE
        </span>


        <div
          style={{
            display:
              "flex",
            flexDirection:
              "column",
            gap:
              "8px",
            marginTop:
              "10px",
          }}
        >
          {whySelected.length >
          0 ? (
            whySelected.map(
              (
                item,
                index,
              ) => (
                <div
                  key={`${recommended.id}-${index}`}
                  style={{
                    display:
                      "flex",
                    gap:
                      "10px",
                    alignItems:
                      "flex-start",
                    padding:
                      "9px 10px",
                    border:
                      "1px solid var(--border)",
                    borderRadius:
                      "7px",
                    background:
                      "rgba(8, 22, 37, 0.52)",
                  }}
                >
                  <span
                    style={{
                      width:
                        "18px",
                      height:
                        "18px",
                      minWidth:
                        "18px",
                      display:
                        "grid",
                      placeItems:
                        "center",
                      borderRadius:
                        "50%",
                      color:
                        "var(--good)",
                      background:
                        "var(--good-soft)",
                      fontSize:
                        "9px",
                      fontWeight:
                        "900",
                    }}
                  >
                    ✓
                  </span>

                  <span
                    style={{
                      color:
                        "#9bb0c5",
                      fontSize:
                        "10px",
                      lineHeight:
                        "1.5",
                    }}
                  >
                    {item}
                  </span>
                </div>
              ),
            )
          ) : (
            <div
              className="simulation-notice"
              style={{
                margin:
                  "0",
              }}
            >
              No detailed selection evidence was attached to this recommendation.
            </div>
          )}
        </div>
      </div>


      <div
        className="simulation-notice"
        style={{
          margin:
            "0 20px 20px",
        }}
      >
        AERIS uses deterministic engine evidence
        for operational calculations. The agent
        interprets and compares that evidence;
        it does not invent aviation metrics.
      </div>
    </section>
  );
}