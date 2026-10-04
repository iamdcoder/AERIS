# Two-Person Parallel Workflow

## Golden rule

Both developers work at the same time, but neither should need to edit the other's owned directories.

## Parallel pattern

```text
                  PHASE GATE
                 /          \
        Person 1              Person 2
        Engine                Agent + UI
          ↓                      ↓
    contract fixture         same fixture
          ↓                      ↓
    deterministic result     mock result
          \                    /
           ---- Integration ----
```

### Every phase has 4 steps

1. Build independently.
2. Test independently.
3. Demonstrate against the contract.
4. Integrate only after both exit gates pass.

### Never block on the other person

Person 1 builds against fixed contract inputs and expected outputs.
Person 2 builds with deterministic mocks that match the contracts.

### Never hide integration work

Use explicit adapter layers. Avoid direct cross-imports into private engine internals.
