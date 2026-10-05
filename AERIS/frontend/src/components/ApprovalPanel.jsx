import React from "react";


export default function ApprovalPanel({
  candidate,
  approvalStatus,
  executionStatus,
  verificationStatus,
  onApprove,
  onReject,
  disabled,
}) {
  const [
    reason,
    setReason,
  ] = React.useState("");


  const pending =
    [
      "PENDING",
      "AWAITING_APPROVAL",
    ].includes(
      String(
        approvalStatus ||
          "PENDING",
      ).toUpperCase(),
    );

  const approved =
    approvalStatus ===
    "APPROVED";

  const rejected =
    approvalStatus ===
    "REJECTED";

  const executed =
    executionStatus ===
    "EXECUTED";

  const finalVerified =
    approvalStatus ===
      "APPROVED" &&
    executionStatus ===
      "EXECUTED" &&
    verificationStatus ===
      "VERIFIED";


  /*
   * Every new recommendation starts a fresh
   * operator-decision cycle.
   *
   * Therefore the previous rejection reason must
   * never remain inside the new rejection field.
   */
  React.useEffect(() => {
    setReason("");
  }, [
    candidate?.id,
  ]);


  function submitReject() {
    const cleanReason =
      reason.trim();

    if (
      !cleanReason
    ) {
      window.alert(
        "A rejection reason is required.",
      );

      return;
    }

    onReject(
      cleanReason,
    );
  }


  let badge =
    "REQUIRED";

  if (
    finalVerified
  ) {
    badge =
      "VERIFIED";
  } else if (
    approved &&
    executed
  ) {
    badge =
      "EXECUTED";
  } else if (
    approved
  ) {
    badge =
      "APPROVED";
  } else if (
    rejected
  ) {
    badge =
      "REJECTED";
  }


  let message =
    "AERIS cannot apply an intervention without human approval.";

  if (
    finalVerified
  ) {
    message =
      "Operator approval recorded. The intervention was executed and the deterministic engine verified the resulting state.";
  } else if (
    approved &&
    executed
  ) {
    message =
      "Operator approval recorded. The intervention executed successfully and is awaiting final state confirmation.";
  } else if (
    approved
  ) {
    message =
      "Operator approval recorded. Execution is authorized.";
  } else if (
    rejected
  ) {
    message =
      "This recommendation was rejected by the operator. AERIS must reassess before execution.";
  }


  return (
    <section className="panel approval-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">
            HUMAN GATE
          </span>

          <h2>
            Operator approval
          </h2>
        </div>

        <span
          className={`approval-status ${
            finalVerified ||
            approved ||
            executed
              ? "approved"
              : rejected
                ? "rejected"
                : "waiting"
          }`}
        >
          {badge}
        </span>
      </div>


      <div className="approval-summary">
        <div className="recommendation-tag">
          {candidate?.id ||
            "—"}
        </div>

        <div>
          <strong>
            {candidate?.label ||
              "No recommendation"}
          </strong>

          <p>
            {candidate?.summary ||
              "AERIS has not produced a recommendation yet."}
          </p>
        </div>
      </div>


      <div className="approval-numbers">
        <div>
          <span>
            AERIS score
          </span>

          <strong>
            {candidate?.decisionScore !==
                null &&
              candidate?.decisionScore !==
                undefined
              ? Number(
                  candidate.decisionScore,
                ).toFixed(
                  2,
                )
              : "—"}
          </strong>
        </div>


        <div>
          <span>
            Resilience
          </span>

          <strong>
            {candidate?.resilience !==
                null &&
              candidate?.resilience !==
                undefined
              ? Number(
                  candidate.resilience,
                ).toFixed(
                  2,
                )
              : "—"}
          </strong>
        </div>


        <div>
          <span>
            Stress survival
          </span>

          <strong>
            {candidate?.stressTotal
              ? `${candidate.stressSurvival}/${candidate.stressTotal}`
              : "—"}
          </strong>
        </div>


        <div>
          <span>
            Network delta
          </span>

          <strong>
            {candidate?.networkDelayDeltaMin !==
                null &&
              candidate?.networkDelayDeltaMin !==
                undefined
              ? `${
                  Number(
                    candidate.networkDelayDeltaMin,
                  ) > 0
                    ? "+"
                    : ""
                }${Number(
                  candidate.networkDelayDeltaMin,
                ).toFixed(
                  2,
                )}m`
              : "—"}
          </strong>
        </div>
      </div>


      {pending && (
        <>
          <div className="approval-warning">
            AERIS cannot apply an intervention without human approval.
          </div>


          <div className="approval-actions">
            <button
              type="button"
              className="button-primary"
              disabled={
                disabled ||
                !candidate?.feasible ||
                candidate?.operatorRejected
              }
              onClick={
                onApprove
              }
            >
              APPROVE SIMULATED INTERVENTION
            </button>


            <button
              type="button"
              className="button-danger"
              disabled={
                disabled
              }
              onClick={
                submitReject
              }
            >
              REJECT
            </button>
          </div>


          <textarea
            className="reject-input"
            placeholder="Reason for rejection (required only when rejecting)"
            value={
              reason
            }
            onChange={(
              event,
            ) =>
              setReason(
                event.target
                  .value,
              )
            }
            disabled={
              disabled
            }
          />
        </>
      )}


      {finalVerified && (
        <div className="approval-confirmation success">
          Final state:{" "}
          <strong>
            HUMAN APPROVED · EXECUTED · VERIFIED
          </strong>
        </div>
      )}


      {approved &&
        !finalVerified && (
        <div className="approval-confirmation success">
          {message}
        </div>
      )}


      {rejected && (
        <div className="approval-confirmation rejected">
          {message}
        </div>
      )}
    </section>
  );
}