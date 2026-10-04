# AERIS Decision Scoring

## 1. Why scoring exists

AERIS separates **feasibility** from **preference**.

The hard-constraint validator decides whether an intervention is operationally possible in the simulated environment. The decision scorer then compares feasible candidates using multiple objectives.

This prevents the system from turning a high score into permission to violate a hard constraint.

---

## 2. Current weights

The implemented default `DecisionWeights` are:

| Component | Weight |
|---|---:|
| Target-flight benefit | 0.25 |
| Network resilience | 0.25 |
| Network impact score | 0.20 |
| Fuel safety margin | 0.15 |
| Future robustness | 0.15 |
| **Total** | **1.00** |

The scorer validates that the configured weights sum to exactly 1.0 within the implementation tolerance.

---

## 3. Normalization configuration

The current default normalization parameters are:

```text
target_delay_ceiling_min       15.0
network_delay_sensitivity_min   20.0
fuel_margin_floor_kg             0.0
fuel_margin_target_kg          600.0
safe_sector_utilization          0.80
```

These parameters determine how raw operational metrics are converted into comparable component scores.

---

## 4. Candidate metrics

Each candidate can carry:

```text
candidate_id
feasible
target_delay_min
added_distance_km
fuel_margin_kg
affected_flights
network_delay_delta_min
peak_sector_utilization
network_resilience
stress_passed
stress_total
second_intervention_probability
local_score
rejection_reasons
```

The scorer turns those raw metrics into component scores and then computes a weighted decision score.

---

## 5. Ranking behavior

Candidates are sorted so that:

1. feasible candidates are considered before infeasible candidates;
2. higher decision score ranks higher among feasible candidates;
3. network ripple is available as a tie-breaking signal;
4. candidate ID provides deterministic final ordering.

Infeasible candidates therefore cannot win merely because their raw local metrics look attractive.

---

## 6. Regret

AERIS tracks two useful comparison concepts:

### Decision regret

The difference between the feasible leader's decision score and the candidate's score.

### Local regret

The difference between the best local score and the candidate's local score.

The second measure is important for the flagship story because it reveals the difference between:

```text
local optimization
```

and:

```text
network-resilient selection
```

---

## 7. Flagship scoring story

The flagship data intentionally creates a strong contrast.

```text
ALT-A
Local score                 0.92
Decision score              0.13
Network delta             +22.03 min
Stress survival             0/5
Resilience                  0.00

ALT-D
Local score                 0.63
Decision score              0.36
Network delta             +12.49 min
Stress survival             4/5
Resilience                  0.80
```

The value of AERIS is not that ALT-D has the highest local score. It is that the decision process considers the wider network and future states before making the final recommendation.

---

## 8. Critic interaction

The scorer produces a preliminary ranking. The critic then challenges the leading candidate using additional deterministic evidence.

The synthesizer can select a replacement when the critic identifies a stronger surviving alternative.

This gives the decision path a two-stage character:

```text
score / rank
     ↓
critic challenge
     ↓
final synthesis
```

The agent therefore does not treat the first ranking result as unquestionable.
