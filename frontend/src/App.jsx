import AirspaceMap from './components/AirspaceMap'
import DisruptionAlert from './components/DisruptionAlert'
import CandidateCards from './components/CandidateCards'
import MetricsPanel from './components/MetricsPanel'
import AgentDecisionTrail from './components/AgentDecisionTrail'
import ApprovalPanel from './components/ApprovalPanel'
import VerificationPanel from './components/VerificationPanel'

export default function App() {
  return (
    <main className="app">
      <header className="topbar">
        <div><strong>AERIS</strong><span>Agentic Airspace Resilience Copilot</span></div>
        <div className="status">SIMULATION • HUMAN SUPERVISED</div>
      </header>
      <DisruptionAlert />
      <section className="workspace">
        <div className="map-column"><AirspaceMap /></div>
        <aside className="decision-column">
          <MetricsPanel />
          <CandidateCards />
          <ApprovalPanel />
        </aside>
      </section>
      <section className="bottom-grid">
        <AgentDecisionTrail />
        <VerificationPanel />
      </section>
    </main>
  )
}
