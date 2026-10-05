function severityLabel(
  value,
) {
  const text =
    String(
      value ||
        "LOW",
    ).toUpperCase();

  if (
    text ===
    "CRITICAL"
  ) {
    return "CRITICAL";
  }

  if (
    text ===
    "HIGH"
  ) {
    return "HIGH";
  }

  if (
    text ===
    "MEDIUM"
  ) {
    return "MEDIUM";
  }

  return "LOW";
}


function severityClass(
  value,
) {
  const severity =
    severityLabel(
      value,
    );

  if (
    severity ===
    "CRITICAL"
  ) {
    return "critical";
  }

  if (
    severity ===
    "HIGH"
  ) {
    return "high";
  }

  if (
    severity ===
    "MEDIUM"
  ) {
    return "medium";
  }

  return "low";
}


export default function CriticChallengePanel({
  agentState,
}) {
  const stateCritic =
    agentState?.critic_result ||
    null;

  const recommendationCritic =
    agentState?.recommendation
      ?.critic ||
    null;

  const critic =
    stateCritic ||
    recommendationCritic ||
    null;


  const evidence =
    Array.isArray(
      agentState?.evidence,
    )
      ? agentState.evidence
      : [];


  const criticEvidence =
    [...evidence]
      .reverse()
      .find(
        (item) =>
          item?.kind ===
          "CRITIC",
      );


  const criticData =
    criticEvidence?.data ||
    {};


  const findings =
    Array.isArray(
      criticData.findings,
    )
      ? criticData.findings
      : [];


  const failureModes =
    Array.isArray(
      criticData.failure_modes_checked,
    )
      ? criticData.failure_modes_checked
      : [];


  const survivingChecks =
    Array.isArray(
      criticData.surviving_checks,
    )
      ? criticData.surviving_checks
      : [];


  const replacementId =
    criticData.replacement_candidate_id ||
    null;


  const challenged =
    Boolean(
      critic?.challenged ||
        criticData.challenged,
    );


  const summary =
    criticData.summary ||
    critic?.finding ||
    agentState?.recommendation
      ?.critic?.finding ||
    "The critic did not attach a detailed challenge summary.";


  return (
    <section className="panel critic-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">
            ADVERSARIAL REVIEW
          </span>

          <h2>
            Critic challenge
          </h2>
        </div>

        <span
          className={`approval-status ${
            challenged
              ? severityClass(
                  criticData.challenge_severity ||
                    critic?.severity,
                )
              : "approved"
          }`}
        >
          {challenged
            ? "CHALLENGED"
            : "CLEAR"}
        </span>
      </div>


      <div
        style={{
          padding:
            "16px 20px",
        }}
      >
        <div
          style={{
            padding:
              "12px 13px",
            border:
              `1px solid ${
                challenged
                  ? "rgba(255, 115, 115, 0.18)"
                  : "rgba(86, 221, 161, 0.18)"
              }`,
            borderRadius:
              "8px",
            background:
              challenged
                ? "rgba(255, 115, 115, 0.045)"
                : "rgba(86, 221, 161, 0.045)",
          }}
        >
          <span
            className="eyebrow"
          >
            OUTCOME
          </span>

          <p
            style={{
              margin:
                "7px 0 0",
              color:
                "#9bb0c5",
              fontSize:
                "10px",
              lineHeight:
                "1.55",
            }}
          >
            {summary}
          </p>
        </div>
      </div>


      <div
        style={{
          padding:
            "0 20px 16px",
        }}
      >
        <span
          className="eyebrow"
        >
          FAILURE MODES CHECKED
        </span>


        <div
          style={{
            display:
              "grid",
            gridTemplateColumns:
              "repeat(2, 1fr)",
            gap:
              "7px",
            marginTop:
              "10px",
          }}
        >
          {failureModes.length >
          0 ? (
            failureModes.map(
              (
                mode,
              ) => (
                <div
                  key={
                    mode
                  }
                  style={{
                    display:
                      "flex",
                    alignItems:
                      "center",
                    gap:
                      "8px",
                    padding:
                      "8px 9px",
                    border:
                      "1px solid var(--border)",
                    borderRadius:
                      "7px",
                    background:
                      "rgba(8, 22, 37, 0.55)",
                  }}
                >
                  <span
                    style={{
                      color:
                        "var(--good)",
                      fontSize:
                        "10px",
                      fontWeight:
                        "900",
                    }}
                  >
                    ✓
                  </span>

                  <span
                    style={{
                      color:
                        "#91a7ba",
                      fontSize:
                        "9px",
                    }}
                  >
                    {String(
                      mode,
                    )
                      .replaceAll(
                        "_",
                        " ",
                      )}
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
                gridColumn:
                  "1 / -1",
              }}
            >
              Critic failure-mode metadata is unavailable for this run.
            </div>
          )}
        </div>
      </div>


      <div
        style={{
          borderTop:
            "1px solid var(--border)",
          padding:
            "16px 20px 18px",
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
            marginBottom:
              "10px",
          }}
        >
          <span
            className="eyebrow"
          >
            MATERIAL FINDINGS
          </span>

          <span
            style={{
              color:
                "var(--muted-2)",
              fontSize:
                "9px",
            }}
          >
            {findings.length} finding
            {findings.length ===
            1
              ? ""
              : "s"}
          </span>
        </div>


        <div
          style={{
            display:
              "flex",
            flexDirection:
              "column",
            gap:
              "9px",
          }}
        >
          {findings.length >
          0 ? (
            findings.map(
              (
                finding,
                index,
              ) => (
                <div
                  key={`${finding.category}-${index}`}
                  style={{
                    padding:
                      "11px 12px",
                    border:
                      "1px solid var(--border)",
                    borderRadius:
                      "8px",
                    background:
                      "rgba(8, 22, 37, 0.62)",
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
                        "12px",
                    }}
                  >
                    <strong
                      style={{
                        fontSize:
                          "10px",
                        letterSpacing:
                          "0.04em",
                      }}
                    >
                      {String(
                        finding.category ||
                          "RISK",
                      )
                        .replaceAll(
                          "_",
                          " ",
                        )}
                    </strong>

                    <span
                      style={{
                        color:
                          finding.severity ===
                          "CRITICAL"
                            ? "var(--danger)"
                            : finding.severity ===
                                "HIGH"
                              ? "var(--warning)"
                              : "var(--muted)",
                        fontSize:
                          "8px",
                        fontWeight:
                          "900",
                        letterSpacing:
                          "0.07em",
                      }}
                    >
                      {severityLabel(
                        finding.severity,
                      )}
                    </span>
                  </div>


                  <p
                    style={{
                      margin:
                        "7px 0 0",
                      color:
                        "#9bb0c5",
                      fontSize:
                        "9px",
                      lineHeight:
                        "1.5",
                    }}
                  >
                    {
                      finding.condition
                    }
                  </p>


                  {finding.evidence && (
                    <div
                      style={{
                        marginTop:
                          "7px",
                        padding:
                          "7px 8px",
                        borderRadius:
                          "6px",
                        background:
                          "rgba(255, 115, 115, 0.045)",
                        color:
                          "#d99292",
                        fontSize:
                          "9px",
                        lineHeight:
                          "1.4",
                      }}
                    >
                      Evidence:{" "}
                      {
                        finding.evidence
                      }
                    </div>
                  )}


                  {finding.mitigation && (
                    <div
                      style={{
                        marginTop:
                          "7px",
                        color:
                          "var(--muted-2)",
                        fontSize:
                          "9px",
                        lineHeight:
                          "1.45",
                      }}
                    >
                      Mitigation:{" "}
                      {
                        finding.mitigation
                      }
                    </div>
                  )}
                </div>
              ),
            )
          ) : (
            <div
              style={{
                padding:
                  "11px",
                border:
                  "1px solid var(--border)",
                borderRadius:
                  "8px",
                color:
                  "var(--muted)",
                background:
                  "rgba(8, 22, 37, 0.55)",
                fontSize:
                  "9px",
                lineHeight:
                  "1.5",
              }}
            >
              The critic did not report
              a material failure finding
              for the current leader.
            </div>
          )}
        </div>
      </div>


      <div
        style={{
          display:
            "grid",
          gridTemplateColumns:
            "1fr 1fr",
          gap:
            "10px",
          padding:
            "0 20px 20px",
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
              "rgba(8, 22, 37, 0.55)",
          }}
        >
          <span
            className="eyebrow"
          >
            CHALLENGED CANDIDATE
          </span>

          <strong
            style={{
              display:
                "block",
              marginTop:
                "6px",
              fontSize:
                "14px",
              color:
                challenged
                  ? "var(--danger)"
                  : "#deedfa",
            }}
          >
            {critic?.candidate_id ||
              "—"}
          </strong>
        </div>


        <div
          style={{
            padding:
              "11px",
            border:
              "1px solid var(--border)",
            borderRadius:
              "7px",
            background:
              "rgba(8, 22, 37, 0.55)",
          }}
        >
          <span
            className="eyebrow"
          >
            REPLACEMENT
          </span>

          <strong
            style={{
              display:
                "block",
              marginTop:
                "6px",
              fontSize:
                "14px",
              color:
                replacementId
                  ? "var(--good)"
                  : "var(--muted)",
            }}
          >
            {replacementId ||
              "NONE"}
          </strong>
        </div>
      </div>


      {survivingChecks.length >
        0 && (
        <div
          className="simulation-notice"
          style={{
            margin:
              "0 20px 20px",
          }}
        >
          Surviving checks:{" "}
          {survivingChecks.join(
            " · ",
          )}
        </div>
      )}
    </section>
  );
}