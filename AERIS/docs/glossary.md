# AERIS Glossary

| Term | Meaning in AERIS |
|---|---|
| AERIS | Agentic Airspace Resilience Intelligence System |
| Airspace state | Current synthetic aircraft, sector, airport, weather and restriction state |
| Target flight | The aircraft currently being protected or rerouted; flagship target is F102 |
| Candidate | A deterministic intervention option generated for the target flight |
| Feasible | Candidate passed the deterministic hard-constraint checks |
| Network ripple | Simulated change in surrounding network delay / pressure attributable to a candidate |
| Target impact | Candidate's simulated effect on the target flight |
| Resilience | Deterministic metric representing performance across the configured network/future evaluation |
| Stress survival | Number of configured future perturbations a candidate survives |
| Future robustness | Normalized robustness signal derived from future scenario performance |
| Critic | Adversarial decision stage that attempts to find reasons to reconsider the current leader |
| Local leader | Candidate with the strongest local-flight score among feasible options |
| Network winner | Candidate selected after broader network/resilience evidence is considered |
| Decision context | Frozen snapshot tying candidate definitions and downstream results to a specific decision time |
| Human approval | Explicit operator permission required before execution |
| Reassessment | New decision cycle triggered by rejection or verification issues |
| Verification | Post-action deterministic check of the resulting simulated state |
| OCC | Airline Operations Control Center; a conceptual target user environment |
| ATC | Air Traffic Control; AERIS does not replace it |
| BOM | Mumbai airport code used by the synthetic flagship scenario |
| WX-BOM-01 | Synthetic convective weather cell used by the flagship scenario |
| S6 | Synthetic airspace sector whose capacity is reduced in the flagship scenario |
| R-MONSOON-01 | Synthetic temporary airspace restriction activated during the flagship scenario |
