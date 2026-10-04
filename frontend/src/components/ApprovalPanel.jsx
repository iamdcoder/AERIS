import { useState } from "react";

export default function ApprovalPanel({
  candidate,
  approvalStatus,
  onApprove,
  onReject,
  disabled,
}) {
  const [reason, setReason] = useState("");

  const pending = approvalStatus === "PENDING";
  const approved = approvalStatus === "APPROVED";
  const rejected = approvalStatus === "REJECTED";

  return (
    <section className="panel approval-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">HUMAN GATE</span>
          <h2>Operator approval</h2>
        </div>

        <span
          className={`approval-status ${
            approved
              ? "approved"
              : rejected
                ? "rejected"
                : "waiting"
          }`}
        >
          {approved
            ? "APPROVED"
            : rejected
              ? "REJECTED"
              : "REQUIRED"}
        </span>
      </div>

      <div className="approval-summary">
        <div className="recommendation-tag">
          {candidate.id}
        </div>

        <div>
          <strong>{candidate.label}</strong>
          <p>{candidate.summary}</p>
        </div>
      </div>

      <div className="approval-numbers">
        <div>
          <span>AERIS score</span>
          <strong>{candidate.decisionScore?.toFixed(2) ?? "—"}</strong>
        </div>

        <div>
          <span>Resilience</span>
          <strong>{candidate.resilience.toFixed(2)}</strong>
        </div>

        <div>
          <span>Stress survival</span>
          <strong>
            {candidate.stressSurvival}/{candidate.stressTotal}
          </strong>
        </div>

        <div>
          <span>Network delta</span>
          <strong>
            {candidate.networkDelayDeltaMin > 0 ? "+" : ""}
            {candidate.networkDelayDeltaMin}m
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
              disabled={disabled || !candidate.feasible}
              onClick={onApprove}
            >
              APPROVE & EXECUTE
            </button>

            <button
              type="button"
              className="button-danger"
              disabled={disabled}
              onClick={() => onReject(reason)}
            >
              REJECT
            </button>
          </div>

          <textarea
            className="reject-input"
            placeholder="Reason for rejection (required only when rejecting)"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </>
      )}

      {approved && (
        <div className="approval-confirmation success">
          Operator approval recorded. Execution and verification are now
          permitted.
        </div>
      )}

      {rejected && (
        <div className="approval-confirmation rejected">
          Recommendation rejected. AERIS will reassess the remaining
          feasible candidates.
        </div>
      )}
    </section>
  );
}