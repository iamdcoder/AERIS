function Check({
  label,
  status,
  value,
}) {
  let statusColor =
    "#91a7ba";

  if (
    status ===
    "PASS"
  ) {
    statusColor =
      "#56dda1";
  } else if (
    status ===
    "FAIL"
  ) {
    statusColor =
      "#ff7373";
  }

  return (
    <div className="verification-check">
      <span>
        {label}
      </span>

      <strong
        style={{
          color:
            statusColor,
        }}
      >
        {status}
      </strong>

      <small>
        {value}
      </small>
    </div>
  );
}


function formatSigned(
  value,
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "Not reported";
  }

  const number =
    Number(value);

  if (
    !Number.isFinite(
      number,
    )
  ) {
    return "Not reported";
  }

  return `${
    number > 0
      ? "+"
      : ""
  }${number.toFixed(
    2,
  )} min`;
}


function formatFuel(
  verification,
) {
  if (
    verification?.fuelMarginMin !==
      null &&
    verification?.fuelMarginMin !==
      undefined
  ) {
    const value =
      Number(
        verification.fuelMarginMin,
      );

    if (
      Number.isFinite(
        value,
      )
    ) {
      return `${
        value > 0
          ? "+"
          : ""
      }${value.toFixed(
        2,
      )} min reserve margin`;
    }
  }

  if (
    verification?.fuelMarginKg !==
      null &&
    verification?.fuelMarginKg !==
      undefined
  ) {
    const value =
      Number(
        verification.fuelMarginKg,
      );

    if (
      Number.isFinite(
        value,
      )
    ) {
      return `${
        value > 0
          ? "+"
          : ""
      }${value.toFixed(
        0,
      )} kg margin`;
    }
  }

  if (
    verification?.remainingFuelMin !==
      null &&
    verification?.remainingFuelMin !==
      undefined
  ) {
    const value =
      Number(
        verification.remainingFuelMin,
      );

    if (
      Number.isFinite(
        value,
      )
    ) {
      return `${value.toFixed(
        2,
      )} min remaining`;
    }
  }

  return "Not reported";
}


export default function VerificationPanel({
  executionStatus,
  verificationStatus,
  verification,
  executionMode,
}) {
  const verified =
    verificationStatus ===
    "VERIFIED";

  const verifying =
    verificationStatus ===
    "VERIFYING";

  const reassessment =
    verificationStatus ===
    "REASSESSMENT_REQUIRED";

  const failed =
    verificationStatus ===
    "FAILED";

  const hasPostActionEvidence =
    verified ||
    verifying ||
    reassessment ||
    failed;

  const pending =
    !hasPostActionEvidence;


  const targetDelta =
    pending
      ? null
      : verification
          ?.targetDelayDeltaMin;

  const networkDelta =
    pending
      ? null
      : verification
          ?.networkDelayDeltaMin;

  const conflicts =
    pending
      ? null
      : verification
          ?.newConflicts;

  const peak =
    pending
      ? null
      : verification
          ?.peakSectorUtilization;

  const downstreamRisk =
    pending
      ? "UNKNOWN"
      : (
          verification
            ?.downstreamRisk ||
          "UNKNOWN"
        ).toUpperCase();


  const targetStatus =
    targetDelta === null
      ? "N/A"
      : targetDelta <=
          0
        ? "PASS"
        : "FAIL";


  const networkStatus =
    networkDelta === null
      ? "N/A"
      : networkDelta <=
          0
        ? "PASS"
        : "FAIL";


  const conflictStatus =
    conflicts === null
      ? "N/A"
      : conflicts ===
          0
        ? "PASS"
        : "FAIL";


  const peakStatus =
    peak === null
      ? "N/A"
      : peak <=
          1
        ? "PASS"
        : "FAIL";


  const fuelStatus =
    pending
      ? "N/A"
      : (
          verification
            ?.fuelMarginMin !==
            null &&
          verification
            ?.fuelMarginMin !==
            undefined
        )
        ? verification
            .fuelMarginMin >
            0
          ? "PASS"
          : "FAIL"
        : (
            verification
              ?.fuelMarginKg !==
              null &&
            verification
              ?.fuelMarginKg !==
              undefined
          )
          ? verification
              .fuelMarginKg >
              0
            ? "PASS"
            : "FAIL"
          : "N/A";


  const riskStatus =
    downstreamRisk ===
    "UNKNOWN"
      ? "N/A"
      : [
          "HIGH",
          "CRITICAL",
          "SEVERE",
        ].includes(
          downstreamRisk,
        )
        ? "FAIL"
        : "PASS";


  let displayMode =
    executionMode ||
    "ENGINE_PENDING";

  if (
    executionStatus ===
      "LOCKED" &&
    displayMode ===
      "SIMULATION_FALLBACK"
  ) {
    displayMode =
      "AWAITING_APPROVAL";
  }


  let badge =
    "PENDING";

  if (verified) {
    badge =
      "VERIFIED";
  } else if (
    verifying
  ) {
    badge =
      "VERIFYING";
  } else if (
    reassessment
  ) {
    badge =
      "REASSESSMENT";
  } else if (
    failed
  ) {
    badge =
      "FAILED";
  }


  const verifiedAt =
    verification
      ?.verifiedAtMin;


  return (
    <section className="panel verification-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">
            POST-ACTION ASSURANCE
          </span>

          <h2>
            Verification
          </h2>
        </div>

        <span
          className={`verification-badge ${
            verified
              ? "verified"
              : "pending"
          }`}
        >
          {badge}
        </span>
      </div>


      <div className="execution-strip">
        <span>
          Execution
        </span>

        <strong>
          {executionStatus ||
            "LOCKED"}
        </strong>

        <span>
          Mode
        </span>

        <strong>
          {displayMode}
        </strong>
      </div>


      {verified &&
        verifiedAt !==
          null &&
        verifiedAt !==
          undefined && (
        <div className="simulation-notice">
          Verified at{" "}
          <strong>
            T+
            {String(
              verifiedAt,
            ).padStart(
              2,
              "0",
            )}
          </strong>
          {" · "}
          deterministic engine confirmation received.
        </div>
      )}


      <div className="verification-checks">
        <Check
          label="Target change"
          status={
            targetStatus
          }
          value={
            targetDelta ===
            null
              ? "Not reported"
              : formatSigned(
                  targetDelta,
                )
          }
        />


        <Check
          label="Network change"
          status={
            networkStatus
          }
          value={
            networkDelta ===
            null
              ? "Not reported"
              : formatSigned(
                  networkDelta,
                )
          }
        />


        <Check
          label="New conflicts"
          status={
            conflictStatus
          }
          value={
            conflicts ===
            null
              ? "Not reported"
              : String(
                  conflicts,
                )
          }
        />


        <Check
          label="Peak sector"
          status={
            peakStatus
          }
          value={
            peak === null
              ? "Not reported"
              : `${Math.round(
                  peak *
                    100,
                )}%`
          }
        />


        <Check
          label="Fuel reserve"
          status={
            fuelStatus
          }
          value={
            pending
              ? "Not reported"
              : formatFuel(
                  verification,
                )
          }
        />


        <Check
          label="Downstream risk"
          status={
            riskStatus
          }
          value={
            downstreamRisk
          }
        />
      </div>


      {!hasPostActionEvidence && (
        <div className="simulation-notice">
          No post-action verification has run yet. AERIS has not executed the intervention because human approval is still pending.
        </div>
      )}


      {verification?.summary &&
        hasPostActionEvidence && (
        <div className="simulation-notice">
          {
            verification.summary
          }
        </div>
      )}


      {executionMode ===
        "SIMULATION_FALLBACK" &&
        executionStatus !==
          "LOCKED" && (
        <div className="simulation-notice">
          Engine execution was unavailable. AERIS preserved deterministic simulation behavior and did not represent the fallback as live operational execution.
        </div>
      )}
    </section>
  );
}