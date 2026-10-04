# Scaffold Map

The scaffold is deliberately organized into two large ownership islands:

```text
PERSON 1                          PERSON 2
--------                          --------
backend/app/engine/**             copilot/**
backend/app/models/**             frontend/**
backend/data/**                   backend/app/api/**
backend/tests/engine/**           backend/tests/api/**
         \                         /
          \_____ contracts ______/
```

The `contracts/` and `scenarios/` directories are coordination zones, not private ownership zones.
