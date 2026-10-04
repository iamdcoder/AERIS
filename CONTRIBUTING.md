# Contributing to AERIS

## Branches

```text
main
├── engine-dev
└── copilot-ui-dev
```

Person 1 works on `engine-dev`.
Person 2 works on `copilot-ui-dev`.

## Commit style

Use small commits:

```text
feat(engine): add sector capacity model
feat(agent): add candidate evaluation tool
feat(ui): add recommendation panel
fix(engine): correct fuel reserve check
fix(agent): handle rejected candidate
```

## Merge discipline

1. Do not mix ownership areas in a commit.
2. Pull/rebase before starting a large integration.
3. Do not casually rename contract fields.
4. Integration happens in small vertical slices.
5. Run tests before merge.
6. Keep the flagship scenario deterministic.

## Definition of done

A feature is done when it works from the contract to the visible product and has a reproducible test or fixture.
