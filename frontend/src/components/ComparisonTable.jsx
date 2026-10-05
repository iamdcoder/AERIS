function signed(
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

  return `${
    number > 0
      ? "+"
      : ""
  }${number.toFixed(
    2,
  )}`;
}


function score(
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

  return Number.isFinite(
    number,
  )
    ? number.toFixed(
        2,
      )
    : "—";
}


function utilization(
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

  return Number.isFinite(
    number,
  )
    ? `${Math.round(
        number * 100,
      )}%`
    : "—";
}


export default function ComparisonTable({
  candidates,
  selectedId,
}) {
  const leader =
    candidates.find(
      (candidate) =>
        candidate.id ===
          selectedId &&
        candidate.recommendable !== false &&
        !candidate.operatorRejected,
    ) ||
    candidates.find(
      (candidate) =>
        candidate.feasible &&
        candidate.recommendable !== false &&
        !candidate.operatorRejected,
    ) ||
    null;


  return (
    <section className="panel comparison-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">
            DECISION MATRIX
          </span>

          <h2>
            Network-aware comparison
          </h2>
        </div>

        <span className="selected-note">
          Leader:{" "}
          {leader?.id ||
            "—"}
        </span>
      </div>


      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>
                Candidate
              </th>

              <th>
                Feasibility
              </th>

              <th>
                Local score
              </th>

              <th>
                Target delay
              </th>

              <th>
                Network Δ
              </th>

              <th>
                Peak sector
              </th>

              <th>
                Resilience
              </th>

              <th>
                Stress
              </th>

              <th>
                AERIS score
              </th>
            </tr>
          </thead>


          <tbody>
            {candidates.map(
              (candidate) => {
                const selected =
                  candidate.id ===
                    selectedId &&
                  !candidate.operatorRejected;

                const operatorRejected =
                  candidate.operatorRejected ===
                  true;

                const target =
                  candidate.targetDelayMin;

                const network =
                  candidate.networkDelayDeltaMin;

                return (
                  <tr
                    key={
                      candidate.id
                    }
                    className={
                      selected
                        ? "selected-row"
                        : ""
                    }
                  >
                    <td>
                      <strong>
                        {
                          candidate.id
                        }
                      </strong>
                    </td>


                    <td>
                      <span
                        className={`table-status ${
                          operatorRejected || !candidate.feasible
                            ? "bad"
                            : candidate.recommendable === false
                              ? "warn"
                              : "good"
                        }`}
                      >
                        {operatorRejected
                          ? "REJECTED"
                          : !candidate.feasible
                            ? "HARD INVALID"
                            : candidate.recommendable === false
                              ? "FEASIBLE · BLOCKED"
                              : "RECOMMENDABLE"}
                      </span>
                    </td>


                    <td>
                      {score(
                        candidate.localScore,
                      )}
                    </td>


                    <td>
                      {target ===
                        null ||
                      target ===
                        undefined
                        ? "—"
                        : `${signed(
                            target,
                          )} min`}
                    </td>


                    <td
                      className={
                        network ===
                            null ||
                        network ===
                            undefined
                          ? ""
                          : network <=
                              0
                            ? "positive"
                            : "negative"
                      }
                    >
                      {network ===
                        null ||
                      network ===
                        undefined
                        ? "—"
                        : `${signed(
                            network,
                          )} min`}
                    </td>


                    <td>
                      {utilization(
                        candidate.peakSectorUtilization,
                      )}
                    </td>


                    <td>
                      {score(
                        candidate.resilience,
                      )}
                    </td>


                    <td>
                      {candidate.stressTotal
                        ? `${candidate.stressSurvival}/${candidate.stressTotal}`
                        : "—"}
                    </td>


                    <td>
                      <strong>
                        {score(
                          candidate.decisionScore,
                        )}
                      </strong>
                    </td>
                  </tr>
                );
              },
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}