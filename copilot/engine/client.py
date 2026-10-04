"""Copilot adapter over the deterministic engine's stable public facade."""
from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any, Protocol

from backend.app.engine import public

_ADAPTER_LOCK = RLock()
_CANDIDATE_CACHE: dict[tuple[str, str], dict[str, Any]] = {}


class EngineClient(Protocol):
    """Capability interface consumed by Copilot tools and orchestration."""

    def get_airspace_state(self) -> dict[str, Any]: ...
    def get_disruptions(self) -> list[dict[str, Any]]: ...
    def get_target_flight(self, flight_id: str) -> dict[str, Any] | None: ...
    def get_sector_state(self, sector_id: str) -> dict[str, Any] | None: ...
    def get_airport_state(self, airport_id: str) -> dict[str, Any] | None: ...
    def get_weather_state(self) -> list[dict[str, Any]]: ...
    def get_restrictions(self) -> list[dict[str, Any]]: ...
    def get_alternatives(self, flight_id: str) -> list[dict[str, Any]]: ...
    def validate_candidate(self, candidate_id: str) -> dict[str, Any] | None: ...
    def get_simulation_result(self, candidate_id: str) -> dict[str, Any] | None: ...
    def get_stress_test_result(self, candidate_id: str) -> dict[str, Any] | None: ...
    def get_stress_result(self, candidate_id: str) -> dict[str, Any] | None: ...
    def get_network_metrics(self) -> dict[str, Any]: ...
    def score_candidates(self, candidate_ids: list[str]) -> list[dict[str, Any]]: ...
    def apply_intervention(self, candidate_id: str) -> dict[str, Any]: ...
    def verify_state(self, candidate_id: str) -> dict[str, Any]: ...
    def advance_simulation(self, minutes: int = 1) -> dict[str, Any]: ...
    def reset_engine(self) -> None: ...


class RealEngineClient:
    """Stateful adapter that delegates every operational decision to engine.public.

    Instances retain candidate definitions for ID-based tool calls; the actual
    digital-twin and candidate lifecycle state remain owned by public.py.
    Constructing another adapter never resets that shared engine state.
    """

    def __init__(self) -> None:
        self._candidates = _CANDIDATE_CACHE
        self._lock = _ADAPTER_LOCK

    def _resolve_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        with self._lock:
            matches = [
                candidate
                for (_, stored_id), candidate in self._candidates.items()
                if stored_id == candidate_id
            ]
            if not matches:
                return None
            flight_ids = {candidate["flight_id"] for candidate in matches}
            if len(flight_ids) > 1:
                raise ValueError(f"Candidate ID {candidate_id!r} is ambiguous across flights")
            return deepcopy(matches[-1])

    def get_airspace_state(self) -> dict[str, Any]:
        return public.get_airspace_state()

    # Compatibility with the original test client/tool surface.
    def get_state(self) -> dict[str, Any]:
        return self.get_airspace_state()

    def get_disruptions(self) -> list[dict[str, Any]]:
        state = self.get_airspace_state()
        return [
            {
                "type": item.get("event", "ENGINE_EVENT"),
                "time_min": item.get("t"),
                "details": deepcopy(item.get("payload", {})),
            }
            for item in state.get("events", [])
        ]

    def get_target_flight(self, flight_id: str) -> dict[str, Any] | None:
        state = self.get_airspace_state()
        return next((item for item in state.get("aircraft", []) if item.get("id") == flight_id), None)

    def get_sector_state(self, sector_id: str) -> dict[str, Any] | None:
        state = self.get_airspace_state()
        return next((item for item in state.get("sectors", []) if item.get("id") == sector_id), None)

    def get_airport_state(self, airport_id: str) -> dict[str, Any] | None:
        state = self.get_airspace_state()
        return next((item for item in state.get("airports", []) if item.get("id") == airport_id), None)

    def get_weather_state(self) -> list[dict[str, Any]]:
        state = self.get_airspace_state()
        return [
            {**item, "severity": item.get("intensity", "NONE")}
            for item in deepcopy(state.get("weather_cells", []))
        ]

    def get_restrictions(self) -> list[dict[str, Any]]:
        state = self.get_airspace_state()
        return deepcopy(state.get("restrictions", []))

    def get_alternatives(self, flight_id: str) -> list[dict[str, Any]]:
        with self._lock:
            candidates = public.generate_alternatives(flight_id)
            self._candidates = {
                key: candidate
                for key, candidate in self._candidates.items()
                if key[0] != flight_id
            }
            for candidate in candidates:
                key = (flight_id, candidate["candidate_id"])
                self._candidates[key] = deepcopy(candidate)
            return deepcopy(candidates)

    def get_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        return self._resolve_candidate(candidate_id)

    def validate_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        with self._lock:
            candidate = self._resolve_candidate(candidate_id)
            if candidate is None:
                return None
            result = public.validate_candidate(candidate)
            self._candidates[(candidate["flight_id"], candidate_id)].update(deepcopy(result))
            return result

    def get_simulation_result(self, candidate_id: str) -> dict[str, Any] | None:
        with self._lock:
            candidate = self._resolve_candidate(candidate_id)
            if candidate is None:
                return None
            result = public.simulate_candidate(candidate)
            self._candidates[(candidate["flight_id"], candidate_id)]["simulation"] = deepcopy(result)
            return result

    def get_stress_result(self, candidate_id: str) -> dict[str, Any] | None:
        with self._lock:
            candidate = self._resolve_candidate(candidate_id)
            if candidate is None:
                return None
            report = public.stress_test_candidate(candidate)
            report["candidate_id"] = candidate_id
            if report.get("failures"):
                report["critical_failure"] = report["failures"][0].get("reason")
            self._candidates[(candidate["flight_id"], candidate_id)]["stress_report"] = deepcopy(report)
            return report

    def get_stress_test_result(self, candidate_id: str) -> dict[str, Any] | None:
        return self.get_stress_result(candidate_id)

    def get_network_metrics(self) -> dict[str, Any]:
        state = self.get_airspace_state()
        sectors = state.get("sectors", [])
        utilization = {
            item["id"]: item.get("utilization_pct", 0.0)
            for item in sectors
            if "id" in item
        }
        return {
            "time_min": state.get("time_min", 0),
            "sector_utilization_pct": utilization,
            "sectors": deepcopy(sectors),
        }

    def score_candidates(self, candidate_ids: list[str]) -> list[dict[str, Any]]:
        with self._lock:
            candidates = []
            for candidate_id in candidate_ids:
                candidate = self._resolve_candidate(candidate_id)
                if candidate is None:
                    raise ValueError(f"Unknown candidate: {candidate_id}")
                candidates.append(candidate)
            scored = public.score_candidates(candidates)
            for candidate in scored:
                key = (candidate["flight_id"], candidate["candidate_id"])
                stress = candidate.get("stress_report", {})
                resilience = candidate.get("resilience_metrics", {})
                candidate["resilience_score"] = resilience.get("future_robustness", 0.0)
                candidate["confidence"] = resilience.get("future_robustness", 0.0)
                candidate["scenario_survival"] = (
                    f"{stress.get('passed', 0)}/{stress.get('total', 0)}"
                )
                self._candidates[key] = deepcopy(candidate)
            return scored

    def apply_intervention(self, candidate_id: str) -> dict[str, Any]:
        with self._lock:
            if self._resolve_candidate(candidate_id) is None:
                raise ValueError(f"Unknown candidate: {candidate_id}")
            return public.apply_intervention(candidate_id)

    def verify_state(self, candidate_id: str) -> dict[str, Any]:
        return public.verify_state(candidate_id)

    def advance_simulation(self, minutes: int = 1) -> dict[str, Any]:
        return public.advance_simulation(minutes)

    def reset_engine(self) -> None:
        with self._lock:
            public.reset_engine()
            self._candidates.clear()
