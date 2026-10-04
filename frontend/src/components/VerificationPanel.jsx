export default function VerificationPanel({
  executionStatus,
  verificationStatus,
  verification,
  executionMode,
}) {
  const verified = verificationStatus === "VERIFIED";

  return (
    <section className="panel verification-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">POST-ACTION ASSURANCE</span>
          <h2>Verification</h2>
        </div>

        <span
          className={`verification-badge ${
            verified ? "verified" : "pending"
          }`}
        >
          {verified ? "VERIFIED" : verificationStatus}
        </span>
      </div>

      <div className="execution-strip">
        <span>Execution</span>
        <strong>{executionStatus}</strong>

        <span>Mode</span>
        <strong>{executionMode}</strong>
      </div>

      <div className="verification-checks">
        <div className="verification-check">
          <span>Target delay</span>
          <strong>
            {verification.targetDelayDeltaMin <= 0 ? "PASS" : "FAIL"}
          </strong>
          <small>
            {verification.targetDelayDeltaMin > 0 ? "+" : ""}
            {verification.targetDelayDeltaMin} min
          </small>
        </div>

        <div className="verification-check">
          <span>Network delay</span>
          <strong>
            {verification.networkDelayDeltaMin <= 0
              ? "PASS"
              : "FAIL"}
          </strong>
          <small>
            {verification.networkDelayDeltaMin > 0 ? "+" : ""}
            {verification.networkDelayDeltaMin} min
          </small>
        </div>

        <div className="verification-check">
          <span>New conflicts</span>
          <strong>
            {verification.newConflicts === 0 ? "PASS" : "FAIL"}
          </strong>
          <small>{verification.newConflicts}</small>
        </div>

        <div className="verification-check">
          <span>Peak sector</span>
          <strong>
            {verification.peakSectorUtilization < 1
              ? "PASS"
              : "FAIL"}
          </strong>
          <small>
            {Math.round(
              verification.peakSectorUtilization * 100
            )}
            %
          </small>
        </div>

        <div className="verification-check">
          <span>Fuel margin</span>
          <strong>
            {verification.fuelMarginKg > 0 ? "PASS" : "FAIL"}
          </strong>
          <small>{verification.fuelMarginKg} kg</small>
        </div>

        <div className="verification-check">
          <span>Downstream risk</span>
          <strong>
            {["HIGH", "CRITICAL"].includes(
              verification.downstreamRisk
            )
              ? "FAIL"
              : "PASS"}
          </strong>
          <small>{verification.downstreamRisk}</small>
        </div>
      </div>

      {executionMode === "SIMULATION_FALLBACK" && (
        <div className="simulation-notice">
          Engine execution endpoint is unavailable. AERIS has preserved
          deterministic simulation behavior and has not represented the
          fallback as live operational execution.
        </div>
      )}
    </section>
  );
}