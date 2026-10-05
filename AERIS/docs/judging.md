# Judge-Facing Proof Points

## 1. One-sentence description

> **AERIS is a human-supervised agentic airspace resilience copilot that evaluates a flight intervention by its impact on the whole network and its ability to survive future disruptions.**

---

## 2. What is innovative

The differentiator is not “we used an LLM.”

The differentiator is the decision loop:

```text
local flight objective
        +
network consequences
        +
future stress
        +
adversarial challenge
        +
human approval
        +
post-action verification
```

This turns route selection into network-resilience decision support.

---

## 3. The three numbers

Make these prominent:

```text
TARGET BENEFIT
NETWORK RIPPLE
RESILIENCE
```

For the flagship recommendation:

```text
Target impact     +4.49 min
Network ripple   +12.49 min
Resilience         0.80
Stress             4/5
```

---

## 4. The AHA moment

Use the local-vs-network contrast:

```text
ALT-A
Local score ~0.92
Network +22.03 min
Stress 0/5

ALT-D
Local score ~0.66
Network +12.49 min
Stress 4/5
```

The actual copilot flagship proof records ALT-A as the preliminary/local leader, ALT-D as the network leader, and the critic challenging ALT-A before ALT-D is synthesized as the recommendation.

---

## 5. Agentic proof

AERIS is agentic because the system supports a tool-mediated investigation loop rather than a single static LLM prompt.

Observable behavior includes:

- investigating current state;
- querying targeted tools;
- collecting structured evidence;
- planning interventions;
- evaluating alternatives;
- running stress tests;
- challenging the leader;
- synthesizing the recommendation;
- waiting for a human;
- reassessing after rejection.

---

## 6. Technical depth

The project contains:

- a deterministic digital twin;
- explicit hard constraints;
- a route graph and candidate generator;
- multi-flight network simulation;
- future perturbation stress testing;
- deterministic multi-objective scoring;
- an adversarial critic;
- structured agent state;
- evidence IDs and event records;
- approval and rejection lifecycle;
- post-action verification.

---

## 7. Responsible AI

AERIS demonstrates restraint as part of the product design.

```text
LLM ≠ operational authority
LLM ≠ safety calculator
LLM ≠ autonomous clearance system
```

The deterministic engine supplies operational evidence, and the human approval boundary prevents a model output from silently becoming an action.

---

## 8. Good judge questions

### “Why not shortest path?”

Because shortest path can create more downstream delay and can be fragile under future conditions.

### “Why is this agentic rather than deterministic?”

The engine remains deterministic, but the agent orchestrates the investigation, tool usage, evidence gathering, challenge and synthesis around the engine.

### “Why do you need a critic?”

The first ranking can reflect current-state trade-offs. The critic intentionally searches for conditions under which the apparent leader becomes fragile.

### “Can I reject the recommendation?”

Yes. Rejection creates a reassessment cycle and a new human-approval state.

### “What if the LLM fails?”

The hybrid path degrades to deterministic investigation when possible.

---

## 9. What not to claim

Do not claim:

- real-time integration with live air traffic unless separately implemented;
- certified aviation safety;
- replacement of ATC or dispatch authority;
- real-world probabilistic safety guarantees;
- production-scale distributed orchestration.

The project is strongest when its claims remain precise.


## Reproducible proof scripts

Use `PYTHONPATH=backend python scripts/run_flagship.py` for the deterministic engine proof and `PYTHONPATH=backend python scripts/run_agent_flagship.py` for the actual agent/coplilot proof. The latter asserts the local-vs-network reversal, critic challenge, approval gate, verification, and rejection/reassessment behavior.
