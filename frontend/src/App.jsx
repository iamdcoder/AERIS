import {
  useEffect,
  useRef,
  useState,
} from "react";

import AirspaceMap from "./components/AirspaceMap";
import DisruptionAlert from "./components/DisruptionAlert";
import CandidateCards from "./components/CandidateCards";
import ComparisonTable from "./components/ComparisonTable";
import MetricsPanel from "./components/MetricsPanel";
import AgentDecisionTrail from "./components/AgentDecisionTrail";
import DecisionEvidencePanel from "./components/DecisionEvidencePanel";
import CriticChallengePanel from "./components/CriticChallengePanel";
import ApprovalPanel from "./components/ApprovalPanel";
import VerificationPanel from "./components/VerificationPanel";
import FlightDetail from "./components/FlightDetail";
import Timeline from "./components/Timeline";
import LiveOperationsPanel from "./components/LiveOperationsPanel";
import { useWebSocket } from "./hooks/useWebSocket";

import {
  approveCopilotRun,
  fetchBaseline,
  healthCheck,
  rejectCopilotRun,
  resetCopilot,
  resetLiveReplay,
  runCopilotRecommendation,
  startLiveReplay,
  stopLiveReplay,
} from "./lib/api";

import {
  getRecommendedCandidate,
  normalizeAgentState,
  normalizeBaseline,
} from "./lib/dashboardAdapter";


const FLAGSHIP_SCENARIO_ID =
  "mumbai_weather_crisis_v2";

const FLAGSHIP_DECISION_TIME_MIN =
  19;

const LIVE_REPLAY_END_MIN =
  35;

const TARGET_FLIGHT_ID =
  "F102";


const EMPTY_CANDIDATE = {
  id: "—",
  feasible: false,
  localScore: null,
  decisionScore: null,
  targetDelayMin: null,
  networkDelayDeltaMin: null,
  peakSectorUtilization: null,
  resilience: 0,
  stressSurvival: 0,
  stressTotal: 0,
  affectedFlights: null,
  fuelMarginKg: null,
  fuelMarginMin: null,
  extraDistanceKm: null,
  label:
    "Awaiting AERIS investigation",
  interventionType:
    "NONE",
  summary:
    "Run AERIS to investigate the current airspace state.",
  rejectionReason: null,
  operatorRejected: false,
};


function Header({
  mode,
  phase,
  onRun,
  disabled,
  backendStatus,
}) {
  const running =
    phase ===
    "RUNNING";

  const completed =
    phase ===
    "COMPLETE";

  const failed =
    phase ===
    "FAILED";

  const waiting =
    phase ===
    "WAITING_APPROVAL";


  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">
          A
        </div>

        <div>
          <strong>
            AERIS
          </strong>

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
          {" · "}
          DECISION T+
          {String(
            FLAGSHIP_DECISION_TIME_MIN,
          ).padStart(
            2,
            "0",
          )}
        </span>
      </div>


      <div className="header-actions">
        <div
          className={`system-state ${
            backendStatus === "OFFLINE"
              ? "offline"
              : backendStatus === "CHECKING"
                ? "checking"
                : ""
          }`}
        >
          <span />

          {running
            ? "ORCHESTRATING"
            : backendStatus === "OFFLINE"
              ? "BACKEND OFFLINE"
              : backendStatus === "CHECKING"
                ? "CHECKING BACKEND"
                : phase ===
                    "WAITING_APPROVAL"
                  ? "WAITING HUMAN"
                  : mode}
        </div>


        <button
          type="button"
          className="run-button"
          disabled={
            disabled ||
            waiting
          }
          onClick={
            onRun
          }
        >
          {running
            ? "AERIS RUNNING..."
            : waiting
              ? "APPROVAL PENDING"
              : completed
                ? "RERUN AERIS"
                : failed
                  ? "RETRY AERIS"
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
  verificationStatus,
  isReassessment,
  rejectedCandidateId,
}) {
  const hasRecommendation =
    Boolean(
      recommendation?.candidateId,
    );


  let approvalText =
    "HUMAN APPROVAL · NOT RUN";


  if (
    hasRecommendation
  ) {
    if (
      isReassessment
    ) {
      approvalText =
        `PREVIOUSLY REJECTED ${
          rejectedCandidateId ||
          "CANDIDATE"
        } · NEW APPROVAL PENDING`;
    } else {
      approvalText =
        `HUMAN APPROVAL · ${approvalStatus}`;
    }
  }


  const verificationText =
    verificationStatus ===
      "VERIFIED" &&
    !isReassessment
      ? " · VERIFIED"
      : "";


  const recommendationSummary =
    recommendation?.summary ||
    candidate?.summary ||
    "No recommendation has been produced yet. Run the investigation to activate the decision pipeline.";


  return (
    <section className="recommendation-banner">
      <div className="recommendation-main">
        <div className="recommendation-kicker">
          <span />

          {hasRecommendation
            ? "AERIS RECOMMENDATION"
            : "AERIS COMMAND CENTER"}
        </div>


        <div className="recommendation-title-row">
          <h1>
            {candidate.id}
          </h1>

          <span>
            {candidate.label}
          </span>
        </div>


        <p>
          {recommendationSummary}
        </p>
      </div>


      <div className="recommendation-stats">
        <div>
          <span>
            Target impact
          </span>

          <strong>
            {candidate.targetDelayMin ===
            null
              ? "—"
              : `${
                  candidate.targetDelayMin >
                  0
                    ? "+"
                    : ""
                }${candidate.targetDelayMin.toFixed(
                  2,
                )} min`}
          </strong>
        </div>


        <div>
          <span>
            Network ripple
          </span>

          <strong>
            {candidate.networkDelayDeltaMin ===
            null
              ? "—"
              : `${
                  candidate.networkDelayDeltaMin >
                  0
                    ? "+"
                    : ""
                }${candidate.networkDelayDeltaMin.toFixed(
                  2,
                )} min`}
          </strong>
        </div>


        <div>
          <span>
            Resilience
          </span>

          <strong>
            {Number(
              candidate.resilience ||
                0,
            ).toFixed(
              2,
            )}
          </strong>
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


      <div className="recommendation-footer">
        <span>
          {approvalText}
          {verificationText}
        </span>
      </div>
    </section>
  );
}


function LoadingScreen() {
  return (
    <div className="loading-screen">
      <div className="loading-mark">
        A
      </div>

      <strong>
        INITIALIZING AERIS
      </strong>

      <span>
        Loading deterministic airspace state...
      </span>
    </div>
  );
}


function ErrorBanner({
  message,
  onRetry,
}) {
  if (!message) {
    return null;
  }


  return (
    <section className="error-banner">
      <div>
        <strong>
          AERIS BACKEND ERROR
        </strong>

        <span>
          {message}
        </span>
      </div>


      <button
        type="button"
        onClick={
          onRetry
        }
      >
        RETRY
      </button>
    </section>
  );
}


function App() {
  const [
    dashboard,
    setDashboard,
  ] = useState(
    null,
  );


  const [
    agentState,
    setAgentState,
  ] = useState(
    null,
  );


  const [
    selectedCandidateId,
    setSelectedCandidateId,
  ] = useState(
    null,
  );


  const [
    busy,
    setBusy,
  ] = useState(
    false,
  );

  const [
    decisionSubmitting,
    setDecisionSubmitting,
  ] = useState(
    null,
  );

  const decisionActionRef = useRef(null);


  const [
    error,
    setError,
  ] = useState(
    "",
  );


  const [
    liveBusy,
    setLiveBusy,
  ] = useState(
    false,
  );


  const [
    backendStatus,
    setBackendStatus,
  ] = useState(
    "CHECKING",
  );


  const {
    snapshot: liveSnapshot,
    connected: liveConnected,
    transport: liveTransport,
    reconnect: reconnectLive,
  } = useWebSocket();


  useEffect(() => {
    loadBaseline();
  }, []);


  useEffect(() => {
    let disposed = false;

    async function checkBackend() {
      const result = await healthCheck();

      if (disposed) {
        return;
      }

      setBackendStatus(
        result.ok
          ? "CONNECTED"
          : "OFFLINE",
      );
    }

    checkBackend();

    const timer = window.setInterval(
      checkBackend,
      30000,
    );

    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, []);


  useEffect(() => {
    if (
      agentState ||
      !liveSnapshot?.entities?.airspace?.CURRENT
    ) {
      return;
    }

    const airspace =
      liveSnapshot.entities.airspace.CURRENT;

    const network =
      {
        total_flights:
          Array.isArray(airspace.aircraft)
            ? airspace.aircraft.length
            : undefined,
        airborne_flights:
          Array.isArray(airspace.aircraft)
            ? airspace.aircraft.filter(
                (flight) =>
                  flight.status === "AIRBORNE",
              ).length
            : undefined,
        holding_flights:
          Array.isArray(airspace.aircraft)
            ? airspace.aircraft.filter(
                (flight) =>
                  flight.status === "HOLDING",
              ).length
            : undefined,
      };

    const normalized =
      normalizeBaseline({
        airspace,
        disruptions: {
          weather_cells:
            airspace.weather_cells || [],
          restrictions:
            airspace.restrictions || [],
        },
        network,
        flight:
          (airspace.aircraft || []).find(
            (flight) =>
              flight.id === TARGET_FLIGHT_ID,
          ),
      });

    setDashboard(normalized);
  }, [agentState, liveSnapshot]);


  async function loadBaseline() {
    setError("");


    const result =
      await fetchBaseline(
        TARGET_FLIGHT_ID,
      );


    if (!result.ok) {
      setError(
        result.error ||
          "Unable to load the AERIS baseline.",
      );

      return;
    }


    const baseline =
      normalizeBaseline(
        result.data,
      );


    setDashboard(
      baseline,
    );


    setAgentState(
      null,
    );


    setSelectedCandidateId(
      null,
    );
  }


  async function handleLiveStart() {
    if (liveBusy || busy) {
      return;
    }

    setLiveBusy(true);
    setError("");
    setAgentState(null);
    setSelectedCandidateId(null);

    const result = await startLiveReplay({
      stopAtMinute: LIVE_REPLAY_END_MIN,
      resetFirst: true,
    });

    setLiveBusy(false);

    if (!result.ok) {
      setError(
        result.error ||
          "Unable to start the live operational replay.",
      );
      return;
    }

    reconnectLive();

    if (result.data) {
      const airspace =
        result.data.entities?.airspace?.CURRENT;

      if (airspace) {
        setDashboard(
          normalizeBaseline({
            airspace,
            disruptions: {
              weather_cells:
                airspace.weather_cells || [],
              restrictions:
                airspace.restrictions || [],
            },
            flight:
              (airspace.aircraft || []).find(
                (flight) =>
                  flight.id === TARGET_FLIGHT_ID,
              ),
          }),
        );
      }
    }
  }


  async function handleLiveStop() {
    if (liveBusy) {
      return;
    }

    setLiveBusy(true);
    const result = await stopLiveReplay();
    setLiveBusy(false);

    if (!result.ok) {
      setError(
        result.error ||
          "Unable to stop the live operational replay.",
      );
    }
  }


  async function handleLiveReset() {
    if (liveBusy || busy) {
      return;
    }

    setLiveBusy(true);
    setError("");
    setAgentState(null);
    setSelectedCandidateId(null);

    const result = await resetLiveReplay();
    setLiveBusy(false);

    if (!result.ok) {
      setError(
        result.error ||
          "Unable to reset the live operational replay.",
      );
      return;
    }

    const airspace =
      result.data?.entities?.airspace?.CURRENT;

    if (airspace) {
      setDashboard(
        normalizeBaseline({
          airspace,
          disruptions: {
            weather_cells:
              airspace.weather_cells || [],
            restrictions:
              airspace.restrictions || [],
          },
          flight:
            (airspace.aircraft || []).find(
              (flight) =>
                flight.id === TARGET_FLIGHT_ID,
            ),
        }),
      );
    }

    reconnectLive();
  }


  async function runAerisAtTime(decisionTimeMin) {
    if (busy || liveBusy) {
      return;
    }

    const decisionTime = Number(decisionTimeMin);
    if (!Number.isInteger(decisionTime) || decisionTime < 0 || decisionTime > 35) {
      setError("Invalid AERIS decision time.");
      return;
    }

    if (liveSnapshot?.running) {
      const stopResult = await stopLiveReplay();
      if (!stopResult.ok) {
        setError(stopResult.error || "Unable to pause the live operational feed.");
        return;
      }
    }

    setBusy(true);
    setError("");
    setAgentState(null);
    setSelectedCandidateId(null);

    try {
      const reset = await resetCopilot();
      if (!reset.ok) {
        setError(reset.error || "Unable to reset the AERIS decision engine.");
        return;
      }

      const runId = `WEB-${Date.now()}-${decisionTime}`;
      const result = await runCopilotRecommendation({
        target_flight_id: TARGET_FLIGHT_ID,
        scenario_id: FLAGSHIP_SCENARIO_ID,
        decision_time_min: decisionTime,
        run_id: runId,
      });

      if (!result.ok) {
        setError(result.error || "AERIS recommendation failed.");
        return;
      }

      const state = result.data;
      setAgentState(state);

      const normalized = normalizeAgentState(state);
      setDashboard(normalized);
      setSelectedCandidateId(normalized.recommendation?.candidateId || null);
    } finally {
      setBusy(false);
    }
  }

  async function runAeris() {
    await runAerisAtTime(FLAGSHIP_DECISION_TIME_MIN);
  }

  async function handleLiveReassess() {
    const liveTime = Number(liveSnapshot?.last_simulation_time_min);
    if (!Number.isInteger(liveTime) || liveTime <= FLAGSHIP_DECISION_TIME_MIN) {
      setError("Advance the live operational feed beyond T+19 before reassessing.");
      return;
    }

    await runAerisAtTime(liveTime);
  }
  function applyDecisionAgentState(state, expectedDecision = null) {
    const normalized = normalizeAgentState(state);
    const rawDecision = String(
      state?.approval?.decision ||
        expectedDecision ||
        normalized.approvalStatus ||
        "PENDING",
    ).toUpperCase();

    const authoritativeDashboard = {
      ...normalized,
      approvalStatus: rawDecision,
    };

    setAgentState(state);
    setDashboard(authoritativeDashboard);

    const nextCandidateId =
      authoritativeDashboard.recommendation?.candidateId ||
      selectedCandidateId ||
      null;

    setSelectedCandidateId(nextCandidateId);

    return authoritativeDashboard;
  }

  async function handleApprove() {
    if (
      !agentState ||
      busy ||
      decisionSubmitting ||
      decisionActionRef.current
    ) {
      return;
    }

    const runId = agentState.run_id;
    if (!runId) {
      setError("AERIS cannot approve a run without a valid run ID. Run AERIS again.");
      return;
    }

    decisionActionRef.current = "APPROVE";
    setDecisionSubmitting("APPROVE");
    setError("");

    try {
      const result = await approveCopilotRun({
        run_id: runId,
        decided_by: "demo_dispatcher",
      });

      if (!result.ok) {
        if (result.errorType === "NOT_FOUND") {
          setAgentState(null);
          setSelectedCandidateId(null);
          await loadBaseline();
          setError(
            "This AERIS run is stale because the backend no longer has it. Run AERIS again.",
          );
        } else {
          setError(result.error || "Approval failed.");
        }
        return;
      }

      applyDecisionAgentState(result.data, "APPROVED");
    } finally {
      decisionActionRef.current = null;
      setDecisionSubmitting(null);
    }
  }

  async function handleReject(rejectionReason) {
    const cleanReason = String(rejectionReason || "").trim();

    if (!cleanReason) {
      window.alert("A rejection reason is required.");
      return;
    }

    if (
      !agentState ||
      busy ||
      decisionSubmitting ||
      decisionActionRef.current
    ) {
      return;
    }

    const runId = agentState.run_id;
    if (!runId) {
      setError("AERIS cannot reject a run without a valid run ID. Run AERIS again.");
      return;
    }

    decisionActionRef.current = "REJECT";
    setDecisionSubmitting("REJECT");
    setError("");

    try {
      const result = await rejectCopilotRun({
        run_id: runId,
        reason: cleanReason,
        decided_by: "demo_dispatcher",
      });

      if (!result.ok) {
        if (result.errorType === "NOT_FOUND") {
          setAgentState(null);
          setSelectedCandidateId(null);
          await loadBaseline();
          setError(
            "This AERIS run is stale because the backend no longer has it. Run AERIS again.",
          );
        } else {
          setError(result.error || "Recommendation rejection failed.");
        }
        return;
      }

      applyDecisionAgentState(result.data, "REJECTED");
    } finally {
      decisionActionRef.current = null;
      setDecisionSubmitting(null);
    }
  }


  function handleCandidateSelect(
    candidateId,
  ) {
    const candidate =
      dashboard?.candidates?.find(
        (item) =>
          item.id ===
          candidateId,
      );


    if (
      !candidate ||
      !candidate.feasible ||
      candidate.operatorRejected
    ) {
      return;
    }


    setSelectedCandidateId(
      candidateId,
    );
  }


  const selectedCandidate =
    dashboard?.candidates?.find(
      (candidate) =>
        candidate.id ===
        selectedCandidateId,
    ) ||
    getRecommendedCandidate(
      dashboard,
    ) ||
    EMPTY_CANDIDATE;


  const recommendedCandidate =
    getRecommendedCandidate(
      dashboard,
    ) ||
    EMPTY_CANDIDATE;


  const approvalStatus =
    dashboard?.approvalStatus ||
    "PENDING";


  let phase =
    "IDLE";


  if (
    busy
  ) {
    phase =
      "RUNNING";
  } else if (
    !agentState
  ) {
    phase =
      "IDLE";
  } else if (
    dashboard?.agentStage ===
      "HUMAN_APPROVAL" &&
    dashboard?.recommendation
  ) {
    phase =
      "WAITING_APPROVAL";
  } else if (
    dashboard?.agentStage ===
      "DEGRADED"
  ) {
    phase =
      "DEGRADED";
  } else if (
    dashboard?.verificationStatus ===
    "VERIFIED"
  ) {
    phase =
      "COMPLETE";
  } else if (
    dashboard?.agentStage ===
    "FAILED"
  ) {
    phase =
      "FAILED";
  } else {
    phase =
      "COMPLETE";
  }


  const waitingForApproval =
    Boolean(
      agentState &&
        dashboard?.recommendation &&
        [
          "PENDING",
          "AWAITING_APPROVAL",
        ].includes(
          String(
            approvalStatus ||
              "PENDING",
          ).toUpperCase(),
        ) &&
        (
          dashboard?.agentStage ===
            "HUMAN_APPROVAL" ||
          dashboard?.isReassessment
        ),
    );


  if (
    !dashboard
  ) {
    return (
      <div className="app-shell">
        <LoadingScreen />
      </div>
    );
  }


  return (
    <div className="app-shell">
      <Header
        mode={
          dashboard.mode
        }
        phase={
          phase
        }
        onRun={
          runAeris
        }
        disabled={
          busy ||
          liveBusy
        }
        backendStatus={
          backendStatus
        }
      />


      <main className="command-center">
        <ErrorBanner
          message={
            error
          }
          onRetry={
            loadBaseline
          }
        />


        <section className="operational-strip">
          <div>
            <span className="eyebrow">
              SYSTEM STATUS
            </span>

            <strong>
              {busy
                ? "AERIS INVESTIGATING..."
                : dashboard.agentStage ===
                    "DEGRADED" &&
                  dashboard.recommendation === null
                  ? "NO ROBUST INTERVENTION AVAILABLE"
                  : dashboard.agentStage ===
                      "HUMAN_APPROVAL" &&
                    dashboard.recommendation
                    ? "WAITING HUMAN"
                    : dashboard.verificationStatus ===
                      "VERIFIED"
                    ? "VERIFIED"
                    : agentState
                      ? String(
                          agentState.status ||
                            "READY",
                        ).replaceAll(
                          "_",
                          " ",
                        )
                      : "OPERATIONAL SIMULATION READY"}
            </strong>
          </div>


          <div>
            <span className="eyebrow">
              TARGET
            </span>

            <strong>
              {
                dashboard
                  .targetFlight
                  .callsign
              }

              {" · "}

              {
                dashboard
                  .targetFlight
                  .id
              }
            </strong>
          </div>


          <div>
            <span className="eyebrow">
              URGENCY
            </span>

            <strong className="text-high">
              {agentState
                ?.diagnosis
                ?.urgency ||
                "HIGH"}
            </strong>
          </div>


          <div>
            <span className="eyebrow">
              SIMULATION TIME
            </span>

            <strong>
              T+
              {String(
                dashboard.simulationTimeMin,
              ).padStart(
                2,
                "0",
              )}
            </strong>
          </div>


          <div>
            <span className="eyebrow">
              AIRPORT
            </span>

            <strong>
              {
                dashboard.airport.id
              }
            </strong>
          </div>
        </section>


        <RecommendationBanner
          candidate={
            recommendedCandidate
          }
          recommendation={
            dashboard.recommendation
          }
          approvalStatus={
            approvalStatus
          }
          verificationStatus={
            dashboard.verificationStatus
          }
          isReassessment={
            dashboard.isReassessment
          }
          rejectedCandidateId={
            dashboard.rejectedCandidateId
          }
        />


        <LiveOperationsPanel
          snapshot={
            liveSnapshot
          }
          connected={
            liveConnected
          }
          transport={
            liveTransport
          }
          onStart={
            handleLiveStart
          }
          onStop={
            handleLiveStop
          }
          onReset={
            handleLiveReset
          }
          onReassess={
            handleLiveReassess
          }
          canReassess={
            Number(liveSnapshot?.last_simulation_time_min ?? 0) >
            FLAGSHIP_DECISION_TIME_MIN
          }
          busy={
            liveBusy ||
            busy
          }
        />


        <div className="dashboard-grid top-grid">
          <div className="main-column">
            <DisruptionAlert
              disruption={
                dashboard.disruption
              }
            />


            <AirspaceMap
              selectedCandidate={
                selectedCandidate
              }
              targetFlightId={
                dashboard.targetFlight.id
              }
              sectors={
                dashboard.sectors
              }
              weather={
                dashboard.weather
              }
            />
          </div>


          <div className="side-column">
            <FlightDetail
              flight={
                dashboard.targetFlight
              }
            />


            <MetricsPanel
              network={
                dashboard.network
              }
              selectedCandidate={
                selectedCandidate
              }
            />
          </div>
        </div>


        <div className="dashboard-grid">
          <CandidateCards
            candidates={
              dashboard.candidates
            }
            selectedId={
              selectedCandidate.id
            }
            onSelect={
              handleCandidateSelect
            }
          />


          <AgentDecisionTrail
            currentStage={
              dashboard.agentStage
            }
            approvalStatus={
              approvalStatus
            }
            executionStatus={
              dashboard.executionStatus
            }
            verificationStatus={
              dashboard.verificationStatus
            }
            rejectedCandidate={
              dashboard.rejectedCandidateId
            }
            rejectionReason={
              dashboard.rejectionReason
            }
            isReassessment={
              dashboard.isReassessment
            }
          />
        </div>


        <ComparisonTable
          candidates={
            dashboard.candidates
          }
          selectedId={
            selectedCandidate.id
          }
        />


        {agentState && (
          <div className="dashboard-grid">
            <DecisionEvidencePanel
              candidates={
                dashboard.candidates
              }
              agentState={
                agentState
              }
            />

            <CriticChallengePanel
              agentState={
                agentState
              }
            />
          </div>
        )}


        {dashboard.recommendation && (
          <div className="dashboard-grid lower-grid">
            <ApprovalPanel
              candidate={
                recommendedCandidate
              }
              approvalStatus={
                approvalStatus
              }
              executionStatus={
                dashboard.executionStatus
              }
              verificationStatus={
                dashboard.verificationStatus
              }
              onApprove={
                handleApprove
              }
              onReject={
                handleReject
              }
              disabled={
                !waitingForApproval ||
                busy ||
                Boolean(decisionSubmitting)
              }
              submitting={
                decisionSubmitting
              }
            />


            <VerificationPanel
              executionStatus={
                dashboard.executionStatus
              }
              verificationStatus={
                dashboard.verificationStatus
              }
              verification={
                dashboard.verification
              }
              executionMode={
                dashboard.executionMode
              }
            />
          </div>
        )}


        <Timeline
          items={
            dashboard.timeline
          }
          simulationTimeMin={
            dashboard.simulationTimeMin
          }
        />


        <footer className="app-footer">
          <div>
            <strong>
              AERIS
            </strong>

            <span>
              Human-supervised agentic airspace resilience
            </span>
          </div>


          <div>
            <span>
              DETERMINISTIC ENGINE AUTHORITY
            </span>

            <span>
              •
            </span>

            <span>
              HUMAN APPROVAL REQUIRED
            </span>

            <span>
              •
            </span>

            <span>
              SIMULATION ENVIRONMENT
            </span>
          </div>
        </footer>
      </main>
    </div>
  );
}


export default App;