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


function normalizeStage(
  value,
) {
  return String(
    value || "",
  )
    .replaceAll(
      "_",
      " ",
    )
    .replaceAll(
      "-",
      " ",
    )
    .trim()
    .toUpperCase();
}


function stageClass(
  status,
) {
  if (
    status ===
    "complete"
  ) {
    return "trail-complete";
  }

  if (
    status ===
    "active"
  ) {
    return "trail-active";
  }

  if (
    status ===
    "blocked"
  ) {
    return "trail-blocked";
  }

  return "trail-pending";
}


export default function AgentDecisionTrail({
  currentStage,
  approvalStatus,
  executionStatus,
  verificationStatus,
  rejectedCandidate,
  rejectionReason,
  isReassessment,
}) {
  const normalizedCurrentStage =
    normalizeStage(
      currentStage,
    );

  const index =
    STAGES.indexOf(
      normalizedCurrentStage,
    );


  const getStatus = (
    stage,
    stageIndex,
  ) => {
    if (
      stage ===
      "HUMAN APPROVAL"
    ) {
      if (
        approvalStatus ===
        "APPROVED"
      ) {
        return "complete";
      }

      if (
        approvalStatus ===
        "REJECTED" &&
        !isReassessment
      ) {
        return "blocked";
      }

      if (
        isReassessment
      ) {
        return "active";
      }

      if (
        index >= 6
      ) {
        return "active";
      }

      return "pending";
    }


    if (
      stage ===
      "EXECUTE"
    ) {
      if (
        executionStatus ===
        "EXECUTED"
      ) {
        return "complete";
      }

      if (
        executionStatus ===
        "FAILED"
      ) {
        return "blocked";
      }

      if (
        executionStatus ===
        "EXECUTING"
      ) {
        return "active";
      }

      return "pending";
    }


    if (
      stage ===
      "VERIFY"
    ) {
      if (
        verificationStatus ===
        "VERIFIED"
      ) {
        return "complete";
      }

      if (
        verificationStatus ===
          "FAILED" ||
        verificationStatus ===
          "REASSESSMENT_REQUIRED"
      ) {
        return "blocked";
      }

      if (
        verificationStatus ===
        "VERIFYING"
      ) {
        return "active";
      }

      return "pending";
    }


    if (
      isReassessment &&
      stage ===
        "RECOMMEND"
    ) {
      return "complete";
    }


    if (
      index < 0
    ) {
      return "pending";
    }


    if (
      stageIndex <
      index
    ) {
      return "complete";
    }


    if (
      stageIndex ===
      index
    ) {
      return "active";
    }


    return "pending";
  };


  let approvalDescription =
    "Awaiting operator approval.";

  if (
    approvalStatus ===
    "APPROVED"
  ) {
    approvalDescription =
      "Operator approved the selected intervention.";
  } else if (
    isReassessment
  ) {
    approvalDescription =
      `Previous ${
        rejectedCandidate ||
        "candidate"
      } was rejected. Awaiting approval for the new recommendation.`;
  } else if (
    approvalStatus ===
    "REJECTED"
  ) {
    approvalDescription =
      `Operator rejected ${
        rejectedCandidate ||
        "the recommendation"
      }.`;
  }


  return (
    <section className="panel trail-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">
            AGENT OBSERVABILITY
          </span>

          <h2>
            Decision trail
          </h2>
        </div>

        <span className="privacy-badge">
          OBSERVABLE ACTIONS ONLY
        </span>
      </div>


      <div className="trail-list">
        {STAGES.map(
          (
            stage,
            stageIndex,
          ) => {
            const status =
              getStatus(
                stage,
                stageIndex,
              );

            return (
              <div
                className={`trail-item ${stageClass(
                  status,
                )}`}
                key={
                  stage
                }
              >
                <div className="trail-marker">
                  {status ===
                  "complete"
                    ? "✓"
                    : status ===
                        "active"
                      ? "•"
                      : status ===
                          "blocked"
                        ? "!"
                        : ""}
                </div>


                <div className="trail-content">
                  <strong>
                    {stage}
                  </strong>

                  <span>
                    {stage ===
                      "OBSERVE" &&
                      "Read the current network state and target-flight degradation."}

                    {stage ===
                      "DIAGNOSE" &&
                      "Collected evidence around weather, capacity and congestion."}

                    {stage ===
                      "PLAN" &&
                      "Selected intervention families and requested candidates."}

                    {stage ===
                      "EVALUATE" &&
                      "Applied deterministic feasibility and network-impact checks."}

                    {stage ===
                      "STRESS TEST" &&
                      "Tested leading candidates against future perturbations."}

                    {stage ===
                      "CRITIC" &&
                      "Attempted to break the current leader before recommendation."}

                    {stage ===
                      "RECOMMEND" &&
                      (
                        isReassessment
                          ? `Reassessed after ${
                              rejectedCandidate ||
                              "the previous recommendation"
                            } was rejected.`
                          : "Synthesized the strongest resilient intervention."
                      )}

                    {stage ===
                      "HUMAN APPROVAL" &&
                      approvalDescription}

                    {stage ===
                      "EXECUTE" &&
                      (
                        executionStatus ===
                        "EXECUTED"
                          ? "Intervention applied in simulation."
                          : executionStatus ===
                              "EXECUTING"
                            ? "Intervention is currently being applied."
                            : "Execution is locked until approval."
                      )}

                    {stage ===
                      "VERIFY" &&
                      (
                        verificationStatus ===
                        "VERIFIED"
                          ? "Post-intervention constraints verified."
                          : verificationStatus ===
                              "VERIFYING"
                            ? "Post-intervention verification is running."
                            : verificationStatus ===
                                "REASSESSMENT_REQUIRED"
                              ? "Verification detected degradation and requires reassessment."
                              : "Verification runs after execution."
                      )}
                  </span>
                </div>
              </div>
            );
          },
        )}
      </div>


      {isReassessment &&
        rejectionReason && (
        <div className="simulation-notice">
          Previous operator decision:{" "}
          <strong>
            {rejectedCandidate ||
              "candidate"}
          </strong>
          {" · "}
          {rejectionReason}
        </div>
      )}
    </section>
  );
}