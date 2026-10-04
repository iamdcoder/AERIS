const STAGES = [
  "OBSERVE",
  "DIAGNOSE",
  "PLAN",
  "EVALUATE",
  "STRESS TEST",
  "CRITIC",
  "RECOMMEND",
  "HUMAN APPROVAL",
  "EXECUTE",
  "VERIFY",
];

function stageClass(status) {
  if (status === "complete") return "trail-complete";
  if (status === "active") return "trail-active";
  if (status === "blocked") return "trail-blocked";
  return "trail-pending";
}

export default function AgentDecisionTrail({
  currentStage,
  approvalStatus,
  executionStatus,
  verificationStatus,
  rejectedCandidate,
}) {
  const index = STAGES.indexOf(currentStage);

  const getStatus = (stage, stageIndex) => {
    if (stage === "HUMAN APPROVAL") {
      if (approvalStatus === "APPROVED") return "complete";

      if (approvalStatus === "REJECTED") return "blocked";

      if (index >= 6) return "active";

      return "pending";
    }

    if (stage === "EXECUTE") {
      if (executionStatus === "EXECUTED") return "complete";
      if (executionStatus === "FAILED") return "blocked";
      if (executionStatus === "EXECUTING") return "active";

      return "pending";
    }

    if (stage === "VERIFY") {
      if (verificationStatus === "VERIFIED") return "complete";

      if (
        verificationStatus === "FAILED" ||
        verificationStatus === "REASSESSMENT_REQUIRED"
      ) {
        return "blocked";
      }

      return "pending";
    }

    if (rejectedCandidate && stage === "CRITIC") {
      return "complete";
    }

    if (stageIndex < index) return "complete";
    if (stageIndex === index) return "active";

    return "pending";
  };

  return (
    <section className="panel trail-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">AGENT OBSERVABILITY</span>
          <h2>Decision trail</h2>
        </div>

        <span className="privacy-badge">
          OBSERVABLE ACTIONS ONLY
        </span>
      </div>

      <div className="trail-list">
        {STAGES.map((stage, stageIndex) => {
          const status = getStatus(stage, stageIndex);

          return (
            <div
              className={`trail-item ${stageClass(status)}`}
              key={stage}
            >
              <div className="trail-marker">
                {status === "complete"
                  ? "✓"
                  : status === "active"
                    ? "•"
                    : status === "blocked"
                      ? "!"
                      : ""}
              </div>

              <div className="trail-content">
                <strong>{stage}</strong>

                <span>
                  {stage === "OBSERVE" &&
                    "Read the current network state and target-flight degradation."}

                  {stage === "DIAGNOSE" &&
                    "Collected evidence around weather, capacity and congestion."}

                  {stage === "PLAN" &&
                    "Selected intervention families and requested candidates."}

                  {stage === "EVALUATE" &&
                    "Applied deterministic feasibility and network-impact checks."}

                  {stage === "STRESS TEST" &&
                    "Tested leading candidates against future perturbations."}

                  {stage === "CRITIC" &&
                    "Attempted to break the current leader before recommendation."}

                  {stage === "RECOMMEND" &&
                    "Synthesized the strongest resilient intervention."}

                  {stage === "HUMAN APPROVAL" &&
                    (approvalStatus === "APPROVED"
                      ? "Operator approved the selected intervention."
                      : approvalStatus === "REJECTED"
                        ? "Operator rejected the recommendation."
                        : "Awaiting operator approval.")}

                  {stage === "EXECUTE" &&
                    (executionStatus === "EXECUTED"
                      ? "Intervention applied in simulation."
                      : "Execution is locked until approval.")}

                  {stage === "VERIFY" &&
                    (verificationStatus === "VERIFIED"
                      ? "Post-intervention constraints verified."
                      : "Verification runs after execution.")}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}