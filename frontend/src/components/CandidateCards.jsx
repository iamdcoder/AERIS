function Score({
  score,
}) {
  if (
    score === null ||
    score === undefined
  ) {
    return (
      <span className="score-na">
        —
      </span>
    );
  }

  return (
    <span className="score-value">
      {Number(
        score,
      ).toFixed(2)}
    </span>
  );
}


export default function CandidateCards({
  candidates,
  selectedId,
  onSelect,
}) {
  return (
    <section className="panel candidates-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">
            INTERVENTIONS
          </span>

          <h2>
            Candidate strategies
          </h2>
        </div>

        <span className="candidate-count">
          {candidates.length}
          {" generated"}
        </span>
      </div>


      <div className="candidate-list">
        {candidates.map(
          (candidate) => {
            const selected =
              candidate.id ===
              selectedId;

            const operatorRejected =
              candidate.operatorRejected ===
              true;

            const feasible =
              candidate.feasible ===
                true &&
              !operatorRejected;

            const recommendable =
              feasible &&
              candidate.recommendable !== false;

            const disabled =
              operatorRejected ||
              !candidate.feasible;

            return (
              <button
                key={
                  candidate.id
                }
                type="button"
                className={`candidate-card ${
                  selected
                    ? "selected"
                    : ""
                } ${
                  !candidate.feasible ||
                  operatorRejected
                    ? "infeasible"
                    : ""
                } ${
                  operatorRejected
                    ? "operator-rejected"
                    : ""
                }`}
                onClick={() =>
                  onSelect(
                    candidate.id,
                  )
                }
                disabled={
                  disabled
                }
              >
                <div className="candidate-top">
                  <div className="candidate-name">
                    <span className="candidate-id">
                      {
                        candidate.id
                      }
                    </span>

                    <div>
                      <strong>
                        {
                          candidate.label
                        }
                      </strong>

                      <span>
                        {
                          candidate.interventionType
                        }
                      </span>
                    </div>
                  </div>


                  <div
                    className={`feasibility-badge ${
                      operatorRejected || !feasible
                        ? "fail"
                        : recommendable
                          ? "pass"
                          : "blocked"
                    }`}
                  >
                    {operatorRejected
                      ? "REJECTED"
                      : !feasible
                        ? "HARD INVALID"
                        : recommendable
                          ? "RECOMMENDABLE"
                          : "FEASIBLE · BLOCKED"}
                  </div>
                </div>


                <div className="candidate-score-row">
                  <div>
                    <span>
                      Local
                    </span>

                    <Score
                      score={
                        candidate.localScore
                      }
                    />
                  </div>


                  <div>
                    <span>
                      AERIS
                    </span>

                    <Score
                      score={
                        candidate.decisionScore
                      }
                    />
                  </div>


                  <div>
                    <span>
                      Resilience
                    </span>

                    <Score
                      score={
                        candidate.resilience
                      }
                    />
                  </div>


                  <div>
                    <span>
                      Stress
                    </span>

                    <strong>
                      {candidate.stressTotal
                        ? `${candidate.stressSurvival}/${candidate.stressTotal}`
                        : "—"}
                    </strong>
                  </div>
                </div>


                <p>
                  {operatorRejected
                    ? `Operator rejected this candidate: ${
                        candidate.rejectionReason ||
                        "No reason recorded."
                      }`
                    : !candidate.feasible
                      ? candidate.summary
                      : !recommendable
                        ? `Not promoted for recommendation: ${(candidate.recommendationBlockers || []).join(" ") || "Fails the network-resilience recommendation policy."}`
                        : candidate.summary}
                </p>


                {candidate.rejectionReason &&
                  !operatorRejected && (
                  <div className="candidate-rejection">
                    {
                      candidate.rejectionReason
                    }
                  </div>
                )}
              </button>
            );
          },
        )}
      </div>
    </section>
  );
}