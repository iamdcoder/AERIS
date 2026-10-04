# AERIS Copilot — Person 2

The `copilot/` package contains the agent, investigation,
tool-adapter and product logic owned by Person 2.

---

# Current architecture

```text
                    GEMINI
                      ↓
               AERIS SYSTEM PROMPT
                      ↓
                TOOL DEFINITIONS
                      ↓
              TOOL-CALLING LOOP
                      ↓
                TOOL REGISTRY
                      ↓
                 AERIS TOOLS
                      ↓
              ENGINE ADAPTER
                      ↓
            MOCK / REAL ENGINE