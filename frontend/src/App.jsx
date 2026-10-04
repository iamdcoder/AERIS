import { useEffect, useMemo, useRef, useState } from "react";

import AirspaceMap from "./components/AirspaceMap";
import DisruptionAlert from "./components/DisruptionAlert";
import CandidateCards from "./components/CandidateCards";
import ComparisonTable from "./components/ComparisonTable";
import MetricsPanel from "./components/MetricsPanel";
import AgentDecisionTrail from "./components/AgentDecisionTrail";
import ApprovalPanel from "./components/ApprovalPanel";
import VerificationPanel from "./components/VerificationPanel";
import FlightDetail from "./components/FlightDetail";
import Timeline from "./components/Timeline";

import { DEMO_DASHBOARD, DEMO_TIMELINE } from "./lib/demoData";
import { applyIntervention, verifyIntervention } from "./lib/api";

const INVESTIGATION_STAGES = [
  "OBSERVE",
  "DIAGNOSE",
  "PLAN",
  "EVALUATE",
  "STRESS TEST",
  "CRITIC",
  "RECOMMEND",
];

function Header({ mode, phase, onRun }) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">A</div>

        <div>
          <strong>AERIS</strong>
          <span>
            Agentic Airspace Resilience Intelligence System
          </span>
        </div>
      </div>

      <div className="header-center">
        <span className="header-title">
          AIRSPACE RESILIENCE COMMAND CENTER
        </span>

        <span className="header-scenario">
          MUMBAI WEATHER CRISIS
        </span>
      </div>

      <div className="header-actions">
        <div className="system-state">
          <span />
          {mode}
        </div>

        <button
          type="button"
          className="run-button"
          onClick={onRun}
        >
          {phase === "RUNNING"
            ? "AERIS RUNNING..."
            : phase === "COMPLETE"
              ? "RERUN INVESTIGATION"
              : "RUN AERIS"}
        </button>
      </div>
    </header>
  );
}

function RecommendationBanner({
  candidate,
  recommendation,
  approvalStatus,
}) {
  return (
    <section className="recommendation-banner">
      <div className="recommendation-main">
        <div className="recommendation-kicker">
          <span />
          AERIS RECOMMENDATION
        </div>

        <div className="recommendation-title-row">
          <h1>{candidate.id}</h1>
          <span>{candidate.label}</span>
        </div>

        <p>{recommendation.summary}</p>
      </div>

      <div className="recommendation-stats">
        <div>
          <span>Decision score</span>
          <strong>{recommendation.decisionScore.toFixed(2)}</strong>
        </div>

        <div>
          <span>Resilience</span>
          <strong>{candidate.resilience.toFixed(2)}</strong>
        </div>

        <div>
          <span>Stress</span>
          <strong>
            {candidate.stressSurvival}/{candidate.stressTotal}
          </strong>
        </div>

        <div>
          <span>Approval</span>
          <strong>{approvalStatus}</strong>
        </div>
      </div>
    </section>
  );
}

function App() {
  const [dashboard] = useState(DEMO_DASHBOARD);

  const [selectedCandidateId, setSelectedCandidateId] =
    useState(dashboard.recommendation.candidateId);

  const [phase, setPhase] = useState("IDLE");
  const [stageIndex, setStageIndex] = useState(-1);

  const [approvalStatus, setApprovalStatus] =
    useState("PENDING");

  const [executionStatus, setExecutionStatus] =
    useState("LOCKED");

  const [verificationStatus, setVerificationStatus] =
    useState("PENDING");

  const [executionMode, setExecutionMode] =
    useState("SIMULATION_FALLBACK");

  const [rejectedCandidate, setRejectedCandidate] =
    useState(null);

  const timerRef = useRef(null);

  const availableCandidates = useMemo(
    () =>
      dashboard.candidates.filter(
        (candidate) => !candidate.rejected
      ),
    [dashboard.candidates]
  );

  const selectedCandidate =
    availableCandidates.find(
      (candidate) => candidate.id === selectedCandidateId
    ) || dashboard.candidates.find(
      (candidate) => candidate.id === dashboard.recommendation.candidateId
    );

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
      }
    };
  }, []);

  function stopRun() {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  function startInvestigation() {
    stopRun();

    setPhase("RUNNING");
    setStageIndex(0);
    setApprovalStatus("PENDING");
    setExecutionStatus("LOCKED");
    setVerificationStatus("PENDING");
    setExecutionMode("SIMULATION_FALLBACK");
    setRejectedCandidate(null);
    setSelectedCandidateId(
      dashboard.recommendation.candidateId
    );

    let currentIndex = 0;

    timerRef.current = window.setInterval(() => {
      currentIndex += 1;

      if (currentIndex >= INVESTIGATION_STAGES.length) {
        stopRun();
        setStageIndex(INVESTIGATION_STAGES.length - 1);
        setPhase("COMPLETE");
        return;
      }

      setStageIndex(currentIndex);
    }, 650);
  }

  function handleCandidateSelect(candidateId) {
    const candidate = dashboard.candidates.find(
      (item) => item.id === candidateId
    );

    if (!candidate || !candidate.feasible) {
      return;
    }

    setSelectedCandidateId(candidateId);

    if (phase === "COMPLETE") {
      setApprovalStatus("PENDING");
      setExecutionStatus("LOCKED");
      setVerificationStatus("PENDING");
    }
  }

  async function handleApprove() {
    if (!selectedCandidate || !selectedCandidate.feasible) {
      return;
    }

    setApprovalStatus("APPROVED");
    setExecutionStatus("EXECUTING");
    setVerificationStatus("PENDING");

    const result = await applyIntervention({
      scenario_id: dashboard.scenarioId,
      target_flight_id: dashboard.targetFlight.id,
      candidate_id: selectedCandidate.id,
      approval: {
        decision: "APPROVED",
        operator: "DEMO_OPERATOR",
      },
    });

    if (result.ok) {
      setExecutionMode("ENGINE");
      setExecutionStatus("EXECUTED");
    } else {
      setExecutionMode("SIMULATION_FALLBACK");
      setExecutionStatus("EXECUTED");
    }

    setTimeout(async () => {
      const verification = await verifyIntervention({
        scenario_id: dashboard.scenarioId,
        target_flight_id: dashboard.targetFlight.id,
        candidate_id: selectedCandidate.id,
      });

      if (verification.ok) {
        setExecutionMode("ENGINE");
      }

      setVerificationStatus(
        "VERIFIED"
      );
    }, 550);
  }

  function handleReject(reason) {
    const cleanReason = String(reason || "").trim();

    if (!cleanReason) {
      window.alert(
        "Rejection reason is required before rejecting a recommendation."
      );
      return;
    }

    const currentIndex = dashboard.candidates.findIndex(
      (candidate) => candidate.id === selectedCandidate.id
    );

    const nextCandidate = dashboard.candidates
      .slice(currentIndex + 1)
      .find((candidate) => candidate.feasible);

    setRejectedCandidate(selectedCandidate.id);
    setApprovalStatus("REJECTED");
    setExecutionStatus("LOCKED");
    setVerificationStatus("PENDING");

    window.setTimeout(() => {
      if (nextCandidate) {
        setSelectedCandidateId(nextCandidate.id);
        setApprovalStatus("PENDING");
        setExecutionStatus("LOCKED");
        setVerificationStatus("PENDING");
      }
    }, 900);
  }

  const currentStage =
    stageIndex >= 0
      ? INVESTIGATION_STAGES[stageIndex]
      : "OBSERVE";

  const uiReady =
    phase === "COMPLETE" ||
    approvalStatus === "PENDING" ||
    approvalStatus === "APPROVED";

  return (
    <div className="app-shell">
      <Header
        mode={dashboard.mode}
        phase={phase}
        onRun={startInvestigation}
      />

      <main className="command-center">
        <section className="operational-strip">
          <div>
            <span className="eyebrow">SYSTEM STATUS</span>
            <strong>
              {phase === "RUNNING"
                ? "AERIS investigating..."
                : "Operational simulation ready"}
            </strong>
          </div>

          <div>
            <span className="eyebrow">TARGET</span>
            <strong>
              {dashboard.targetFlight.callsign}
            </strong>
          </div>

          <div>
            <span className="eyebrow">URGENCY</span>
            <strong className="text-high">HIGH</strong>
          </div>

          <div>
            <span className="eyebrow">SIMULATION TIME</span>
            <strong>
              T+
              {String(dashboard.simulationTimeMin).padStart(
                2,
                "0"
              )}
            </strong>
          </div>

          <div>
            <span className="eyebrow">CAPACITY</span>
            <strong>
              {dashboard.airport.arrivalCapacityPer15Min}
              <span className="subtle-unit">
                {" "}
                / {dashboard.airport.normalArrivalCapacityPer15Min}
              </span>
            </strong>
          </div>
        </section>

        <RecommendationBanner
          candidate={selectedCandidate}
          recommendation={dashboard.recommendation}
          approvalStatus={
            phase === "RUNNING"
              ? "ANALYSIS"
              : approvalStatus
          }
        />

        <div className="dashboard-grid top-grid">
          <div className="main-column">
            <DisruptionAlert disruption={dashboard.disruption} />

            <AirspaceMap
              selectedCandidate={selectedCandidate}
              targetFlightId={dashboard.targetFlight.id}
            />
          </div>

          <div className="side-column">
            <FlightDetail flight={dashboard.targetFlight} />

            <MetricsPanel
              network={dashboard.network}
              selectedCandidate={selectedCandidate}
            />
          </div>
        </div>

        <div className="dashboard-grid">
          <CandidateCards
            candidates={dashboard.candidates}
            selectedId={selectedCandidate.id}
            onSelect={handleCandidateSelect}
          />

          <AgentDecisionTrail
            currentStage={currentStage}
            approvalStatus={
              phase === "RUNNING"
                ? "PENDING"
                : approvalStatus
            }
            executionStatus={executionStatus}
            verificationStatus={verificationStatus}
            rejectedCandidate={rejectedCandidate}
          />
        </div>

        <ComparisonTable
          candidates={dashboard.candidates}
          selectedId={selectedCandidate.id}
        />

        <div className="dashboard-grid lower-grid">
          <ApprovalPanel
            candidate={selectedCandidate}
            approvalStatus={approvalStatus}
            onApprove={handleApprove}
            onReject={handleReject}
            disabled={
              !uiReady ||
              phase === "RUNNING" ||
              executionStatus === "EXECUTING"
            }
          />

          <VerificationPanel
            executionStatus={executionStatus}
            verificationStatus={verificationStatus}
            verification={dashboard.verification}
            executionMode={executionMode}
          />
        </div>

        <Timeline
          items={DEMO_TIMELINE}
          simulationTimeMin={dashboard.simulationTimeMin}
        />

        <footer className="app-footer">
          <div>
            <strong>AERIS</strong>
            <span>
              Human-supervised agentic airspace resilience
            </span>
          </div>

          <div>
            <span>DETERMINISTIC ENGINE AUTHORITY</span>
            <span>•</span>
            <span>NO AUTONOMOUS ATC CONTROL</span>
            <span>•</span>
            <span>SIMULATION ENVIRONMENT</span>
          </div>
        </footer>
      </main>
    </div>
  );
}

export default App;