function signed(value) {
  return value > 0 ? `+${value}` : `${value}`;
}

function utilization(value) {
  return `${Math.round(value * 100)}%`;
}

export default function ComparisonTable({
  candidates,
  selectedId,
}) {
  return (
    <section className="panel comparison-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">DECISION MATRIX</span>
          <h2>Network-aware comparison</h2>
        </div>

        <span className="selected-note">
          Leader: {selectedId}
        </span>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Feasibility</th>
              <th>Target delay</th>
              <th>Network Δ</th>
              <th>Peak sector</th>
              <th>Resilience</th>
              <th>Stress</th>
              <th>AERIS score</th>
            </tr>
          </thead>

          <tbody>
            {candidates.map((candidate) => {
              const selected = candidate.id === selectedId;

              return (
                <tr
                  key={candidate.id}
                  className={selected ? "selected-row" : ""}
                >
                  <td>
                    <strong>{candidate.id}</strong>
                  </td>

                  <td>
                    <span
                      className={`table-status ${
                        candidate.feasible ? "good" : "bad"
                      }`}
                    >
                      {candidate.feasible ? "PASS" : "FAIL"}
                    </span>
                  </td>

                  <td>+{candidate.targetDelayMin} min</td>

                  <td
                    className={
                      candidate.networkDelayDeltaMin <= 0
                        ? "positive"
                        : "negative"
                    }
                  >
                    {signed(candidate.networkDelayDeltaMin)} min
                  </td>

                  <td>{utilization(candidate.peakSectorUtilization)}</td>

                  <td>{candidate.resilience.toFixed(2)}</td>

                  <td>
                    {candidate.stressSurvival}/{candidate.stressTotal}
                  </td>

                  <td>
                    <strong>
                      {candidate.decisionScore === null
                        ? "—"
                        : candidate.decisionScore.toFixed(2)}
                    </strong>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}