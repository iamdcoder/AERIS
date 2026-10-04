function Score({ score }) {
  if (score === null || score === undefined) {
    return <span className="score-na">—</span>;
  }

  return <span className="score-value">{score.toFixed(2)}</span>;
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
          <span className="eyebrow">INTERVENTIONS</span>
          <h2>Candidate strategies</h2>
        </div>

        <span className="candidate-count">
          {candidates.length} generated
        </span>
      </div>

      <div className="candidate-list">
        {candidates.map((candidate) => {
          const selected = candidate.id === selectedId;
          const feasible = candidate.feasible;

          return (
            <button
              key={candidate.id}
              type="button"
              className={`candidate-card ${
                selected ? "selected" : ""
              } ${!feasible ? "infeasible" : ""}`}
              onClick={() => onSelect(candidate.id)}
            >
              <div className="candidate-top">
                <div className="candidate-name">
                  <span className="candidate-id">{candidate.id}</span>

                  <div>
                    <strong>{candidate.label}</strong>
                    <span>
                      {candidate.interventionType.replaceAll("_", " ")}
                    </span>
                  </div>
                </div>

                <div
                  className={`feasibility-badge ${
                    feasible ? "pass" : "fail"
                  }`}
                >
                  {feasible ? "FEASIBLE" : "REJECTED"}
                </div>
              </div>

              <div className="candidate-score-row">
                <div>
                  <span>Local</span>
                  <Score score={candidate.localScore} />
                </div>

                <div>
                  <span>AERIS</span>
                  <Score score={candidate.decisionScore} />
                </div>

                <div>
                  <span>Resilience</span>
                  <Score score={candidate.resilience} />
                </div>

                <div>
                  <span>Stress</span>
                  <strong>
                    {candidate.stressSurvival}/{candidate.stressTotal}
                  </strong>
                </div>
              </div>

              <p>{candidate.summary}</p>

              {candidate.rejectionReason && (
                <div className="candidate-rejection">
                  {candidate.rejectionReason}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </section>
  );
}