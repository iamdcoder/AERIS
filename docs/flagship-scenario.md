# Flagship Scenario — Mumbai Monsoon Multi-Constraint Network Crisis

## 1. Scenario identity

```text
ID              mumbai_weather_crisis_v2
Target          F102 / AI102
Duration        35 simulated minutes
Aircraft        40
Airport         BOM
```

The scenario is synthetic. It is designed specifically to make network consequences visible and to create a meaningful critic challenge.

---

## 2. Timeline

| Time | Event | Operational effect |
|---|---|---|
| T+00 | Baseline | 40 aircraft, F102 airborne, BOM normal |
| T+05 | Convective weather | WX-BOM-01 becomes HIGH intensity |
| T+08 | BOM capacity drop | Arrival capacity 18 → 12/hr |
| T+10 | Holding begins | Four selected aircraft accumulate delay |
| T+12 | S6 capacity cut | S6 capacity becomes 6 and traffic pressure rises |
| T+15 | F102 degraded | F102 enters DEGRADED state with 50 min fuel remaining |
| T+17 | Candidate generation | Five deterministic interventions generated |
| T+18 | Restriction activates | R-MONSOON-01 becomes active |
| T+19 | Hard validation | ALT-C and ALT-E rejected |
| T+21 | Frozen decision simulation | ALT-A, ALT-B and ALT-D compared |
| T+24 | Stress test | Five future perturbations evaluated |
| T+26 | Critic | Preliminary leader challenged |
| T+28 | Recommendation | ALT-D selected |
| T+30 | Human approval | Operator approves ALT-D |
| T+32 | Verification | Deterministic engine verifies the result |
| T+35 | Monitoring | Final simulated network state reported |

---

## 3. Initial baseline

The deterministic runner reports:

```text
Total flights          40
Airborne               40
Network delay           0.0 min
BOM capacity           18 arr/hr
F102 fuel              70.0 min
F102 status             AIRBORNE
```

---

## 4. Disruption buildup

The scenario intentionally combines several interacting pressures.

### Weather

`WX-BOM-01` develops near BOM and reaches HIGH intensity with uncertainty.

### Airport capacity

BOM acceptance drops from 18 to 12 arrivals per hour.

### Holding

Selected aircraft enter holding, increasing network delay and fuel consumption.

### Sector pressure

S6 is reduced to capacity 6 while traffic is already high, making the bypass corridor unattractive.

### Target-flight degradation

F102 becomes `DEGRADED` and its usable fuel margin becomes more important to route selection.

### Temporary restriction

`R-MONSOON-01` activates over the FL340 corridor, invalidating ALT-C.

---

## 5. Candidate set

```text
ALT-A — shortest bypass
ALT-B — fuel-efficient south-east
ALT-C — direct high level
ALT-D — sector diversion resilient
ALT-E — conservative west arc
```

The goal is not to make all five candidates equally good. The goal is to produce distinct operational trade-offs.

---

## 6. Hard-constraint results at T+19

```text
ALT-A   FEASIBLE
ALT-B   FEASIBLE
ALT-C   REJECTED → active restriction / altitude condition
ALT-D   FEASIBLE
ALT-E   REJECTED → insufficient fuel reserve
```

Therefore only three candidates proceed to full downstream comparison.

---

## 7. Network simulation

Frozen at the decision snapshot:

| Candidate | Target delay | Network delta | Affected flights |
|---|---:|---:|---:|
| ALT-A | +0.03 min | +22.03 min | 4 |
| ALT-B | +15.38 min | +55.38 min | 5 |
| ALT-D | +4.49 min | +12.49 min | 3 |

The network-level result is the key discriminator.

ALT-A looks excellent if the operator only watches the target flight's immediate delay. It is much worse when the affected network is included.

---

## 8. Stress test

The five deterministic futures are:

```text
F1  Weather expansion +10%
F2  Weather expansion +20%
F3  S6 capacity -15% with future bypass restriction
F4  Traffic demand +15%
F5  BOM acceptance -20%
```

Observed survival:

```text
ALT-A   0/5
ALT-B   0/5
ALT-D   4/5
```

The flagship engine output identifies F4 as the failed ALT-D stress case, where network delay / sector utilization becomes too high. That limitation is useful: AERIS is not claiming that the recommendation is invulnerable, only that it is more robust across the evaluated futures.

---

## 9. Critic challenge

The critic evaluates the preliminary candidate against future fragility signals such as:

```text
FUTURE_ROBUSTNESS
REINTERVENTION
SECTOR_CAPACITY
CONFLICT_RISK
DOWNSTREAM_IMPACT
```

In the flagship story, ALT-A is the local leader but is challenged because it fails future robustness and has a high estimated probability of requiring another intervention.

ALT-D survives the critic as the stronger resilient alternative.

---

## 10. Recommendation

```text
Candidate             ALT-D
Score                  0.36
Target delay           +4.49 min
Network delta          +12.49 min
Resilience              0.80
Stress                  4/5
Future robustness       80%
Re-intervention         20%
```

The important contrast is not “ALT-D is perfect.” The claim is:

> **ALT-D gives a better network-resilience trade-off under the configured deterministic scenario than the locally stronger alternative.**

---

## 11. Human approval

AERIS stops at the approval boundary and waits for the dispatcher/operator.

The successful path is:

```text
RECOMMEND ALT-D
       ↓
HUMAN APPROVAL
       ↓
APPROVED
       ↓
EXECUTED
       ↓
VERIFIED
```

---

## 12. Rejection scenario

The frontend also demonstrates:

```text
RECOMMEND ALT-D
       ↓
HUMAN REJECTS
       ↓
AERIS REASSESSES
       ↓
ALT-D EXCLUDED
       ↓
NEW RECOMMENDATION
       ↓
FRESH HUMAN APPROVAL
```

The current product screenshots confirm that rejecting ALT-D results in a new recommendation and returns execution to the locked / awaiting-approval state.

---

## 13. Why this scenario was chosen

The scenario contains enough interacting constraints to produce the intended AERIS behavior without requiring external aviation data.

It demonstrates:

- feasibility under multiple hard constraints;
- non-local network consequences;
- future uncertainty;
- critic intervention;
- human oversight;
- verification.

---

## 14. Reproducibility

Use:

```bash
PYTHONPATH=backend python scripts/run_flagship.py
```

The runner resets the engine before execution and reports a machine-readable summary at the end.
