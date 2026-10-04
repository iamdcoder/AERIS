from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any, Protocol

from backend.app.engine import public


_ADAPTER_LOCK = RLock()

_CANDIDATE_CACHE: dict[
    tuple[str, str],
    dict[str, Any],
] = {}


class EngineClient(Protocol):
    def get_airspace_state(self) -> dict[str, Any]: ...

    def get_disruptions(self) -> list[dict[str, Any]]: ...

    def get_target_flight(
        self,
        flight_id: str,
    ) -> dict[str, Any] | None: ...

    def get_sector_state(
        self,
        sector_id: str,
    ) -> dict[str, Any] | None: ...

    def get_airport_state(
        self,
        airport_id: str,
    ) -> dict[str, Any] | None: ...

    def get_weather_state(
        self,
    ) -> list[dict[str, Any]]: ...

    def get_restrictions(
        self,
    ) -> list[dict[str, Any]]: ...

    def get_alternatives(
        self,
        flight_id: str,
    ) -> list[dict[str, Any]]: ...

    def validate_candidate(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None: ...

    def get_simulation_result(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None: ...

    def get_stress_test_result(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None: ...

    def get_stress_result(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None: ...

    def get_network_metrics(
        self,
    ) -> dict[str, Any]: ...

    def score_candidates(
        self,
        candidate_ids: list[str],
    ) -> list[dict[str, Any]]: ...

    def apply_intervention(
        self,
        candidate_id: str,
    ) -> dict[str, Any]: ...

    def verify_state(
        self,
        candidate_id: str,
    ) -> dict[str, Any]: ...

    def advance_simulation(
        self,
        minutes: int = 1,
    ) -> dict[str, Any]: ...

    def reset_engine(self) -> None: ...


class RealEngineClient:
    """
    Adapter between Person 2's copilot layer and Person 1's
    deterministic engine facade.

    The adapter does not implement route, fuel, capacity or
    conflict calculations.
    """

    def __init__(self) -> None:
        self._candidates = _CANDIDATE_CACHE
        self._lock = _ADAPTER_LOCK

    def _resolve_candidate(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None:
        with self._lock:
            matches = [
                candidate
                for (_, stored_id), candidate
                in self._candidates.items()
                if stored_id == candidate_id
            ]

            if not matches:
                return None

            flight_ids = {
                candidate["flight_id"]
                for candidate in matches
            }

            if len(flight_ids) > 1:
                raise ValueError(
                    f"Candidate ID {candidate_id!r} "
                    "is ambiguous across flights"
                )

            return deepcopy(
                matches[-1]
            )

    def get_airspace_state(self) -> dict[str, Any]:
        return public.get_airspace_state()

    def get_state(self) -> dict[str, Any]:
        return self.get_airspace_state()

    def get_disruptions(
        self,
    ) -> list[dict[str, Any]]:
        """
        Build operational disruption signals from the current
        deterministic snapshot.

        The engine event log is useful for auditing, but the copilot
        needs current state-derived signals for diagnosis.
        """
        state = self.get_airspace_state()

        disruptions: list[dict[str, Any]] = []

        for cell in state.get(
            "weather_cells",
            [],
        ):
            intensity = str(
                cell.get(
                    "intensity",
                    "NORMAL",
                )
            ).upper()

            if intensity in {
                "NORMAL",
                "LOW",
                "NONE",
                "",
            }:
                continue

            disruptions.append(
                {
                    "type": "WEATHER_EXPANSION",
                    "severity": intensity,
                    "summary": (
                        f"Weather cell "
                        f"{cell.get('id', 'UNKNOWN')} "
                        f"is {intensity.lower()} and may "
                        "constrain the operational corridor."
                    ),
                    "cell_id": cell.get("id"),
                }
            )

        for airport in state.get(
            "airports",
            [],
        ):
            status = str(
                airport.get(
                    "operational_status",
                    "NORMAL",
                )
            ).upper()

            if status in {
                "",
                "NORMAL",
                "OPERATIONAL",
            }:
                continue

            disruptions.append(
                {
                    "type": "AIRPORT_CAPACITY_DEGRADATION",
                    "severity": "HIGH",
                    "summary": (
                        f"Airport "
                        f"{airport.get('id', 'UNKNOWN')} "
                        f"is currently {status.lower()}."
                    ),
                    "airport_id": airport.get("id"),
                }
            )

        for sector in state.get(
            "sectors",
            [],
        ):
            utilization = sector.get(
                "utilization_pct"
            )

            if utilization is None:
                utilization = sector.get(
                    "projected_utilization",
                    0,
                )

            try:
                utilization_value = float(
                    utilization
                )

                # projected_utilization may be represented
                # as 0.92 rather than 92.
                if utilization_value <= 2:
                    utilization_value *= 100
            except (
                TypeError,
                ValueError,
            ):
                continue

            if utilization_value < 85:
                continue

            severity = (
                "CRITICAL"
                if utilization_value >= 100
                else "HIGH"
            )

            disruptions.append(
                {
                    "type": "SECTOR_CONGESTION",
                    "severity": severity,
                    "summary": (
                        f"Sector "
                        f"{sector.get('id', 'UNKNOWN')} "
                        f"is at approximately "
                        f"{utilization_value:.0f}% utilization."
                    ),
                    "sector_id": sector.get("id"),
                    "utilization_pct": round(
                        utilization_value,
                        1,
                    ),
                }
            )

        for restriction in state.get(
            "restrictions",
            [],
        ):
            if restriction.get(
                "active",
                True,
            ):
                disruptions.append(
                    {
                        "type": "AIRSPACE_RESTRICTION",
                        "severity": "HIGH",
                        "summary": (
                            f"Active airspace restriction "
                            f"{restriction.get('id', 'UNKNOWN')} "
                            "is constraining routing."
                        ),
                        "restriction_id": restriction.get(
                            "id"
                        ),
                    }
                )

        return disruptions

    def get_target_flight(
        self,
        flight_id: str,
    ) -> dict[str, Any] | None:
        state = self.get_airspace_state()

        return next(
            (
                item
                for item
                in state.get(
                    "aircraft",
                    [],
                )
                if item.get("id") == flight_id
            ),
            None,
        )

    def get_sector_state(
        self,
        sector_id: str,
    ) -> dict[str, Any] | None:
        state = self.get_airspace_state()

        return next(
            (
                item
                for item
                in state.get(
                    "sectors",
                    [],
                )
                if item.get("id") == sector_id
            ),
            None,
        )

    def get_airport_state(
        self,
        airport_id: str,
    ) -> dict[str, Any] | None:
        state = self.get_airspace_state()

        return next(
            (
                item
                for item
                in state.get(
                    "airports",
                    [],
                )
                if item.get("id") == airport_id
            ),
            None,
        )

    def get_weather_state(
        self,
    ) -> list[dict[str, Any]]:
        state = self.get_airspace_state()

        return [
            {
                **item,
                "severity": item.get(
                    "intensity",
                    "NONE",
                ),
            }
            for item
            in deepcopy(
                state.get(
                    "weather_cells",
                    [],
                )
            )
        ]

    def get_restrictions(
        self,
    ) -> list[dict[str, Any]]:
        state = self.get_airspace_state()

        return deepcopy(
            state.get(
                "restrictions",
                [],
            )
        )

    def get_alternatives(
        self,
        flight_id: str,
    ) -> list[dict[str, Any]]:
        with self._lock:
            candidates = public.generate_alternatives(
                flight_id
            )

            for key in list(
                self._candidates
            ):
                if key[0] == flight_id:
                    del self._candidates[key]

            for candidate in candidates:
                key = (
                    flight_id,
                    candidate["candidate_id"],
                )

                self._candidates[key] = deepcopy(
                    candidate
                )

            return deepcopy(
                candidates
            )

    def get_candidate(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None:
        return self._resolve_candidate(
            candidate_id
        )

    def validate_candidate(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None:
        with self._lock:
            candidate = self._resolve_candidate(
                candidate_id
            )

            if candidate is None:
                return None

            result = public.validate_candidate(
                candidate
            )

            key = (
                candidate["flight_id"],
                candidate_id,
            )

            self._candidates[key].update(
                deepcopy(result)
            )

            return result

    def get_simulation_result(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None:
        with self._lock:
            candidate = self._resolve_candidate(
                candidate_id
            )

            if candidate is None:
                return None

            result = public.simulate_candidate(
                candidate
            )

            key = (
                candidate["flight_id"],
                candidate_id,
            )

            self._candidates[key][
                "simulation"
            ] = deepcopy(result)

            return result

    def get_stress_result(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None:
        with self._lock:
            candidate = self._resolve_candidate(
                candidate_id
            )

            if candidate is None:
                return None

            report = public.stress_test_candidate(
                candidate
            )

            report["candidate_id"] = (
                candidate_id
            )

            failures = report.get(
                "failures"
            )

            if failures:
                report["critical_failure"] = (
                    failures[0].get(
                        "reason"
                    )
                )

            key = (
                candidate["flight_id"],
                candidate_id,
            )

            self._candidates[key][
                "stress_report"
            ] = deepcopy(report)

            return report

    def get_stress_test_result(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None:
        return self.get_stress_result(
            candidate_id
        )

    def get_network_metrics(
        self,
    ) -> dict[str, Any]:
        state = self.get_airspace_state()

        aircraft = state.get(
            "aircraft",
            [],
        )

        sectors = state.get(
            "sectors",
            [],
        )

        total_delay = sum(
            float(
                flight.get(
                    "delay_min",
                    0,
                )
                or 0
            )
            for flight in aircraft
        )

        holding_flights = sum(
            1
            for flight in aircraft
            if str(
                flight.get(
                    "status",
                    "",
                )
            ).upper()
            == "HOLDING"
        )

        utilization = {}

        for sector in sectors:
            value = sector.get(
                "utilization_pct",
                0,
            )

            try:
                value = float(
                    value
                )
            except (
                TypeError,
                ValueError,
            ):
                value = 0.0

            utilization[
                sector.get(
                    "id",
                    "UNKNOWN",
                )
            ] = value

        return {
            "time_min": state.get(
                "time_min",
                0,
            ),
            "total_delay_min": round(
                total_delay,
                2,
            ),
            "airborne_flights": sum(
                1
                for flight in aircraft
                if flight.get(
                    "status"
                )
                == "AIRBORNE"
            ),
            "holding_flights": holding_flights,
            "total_flights": len(
                aircraft
            ),
            "sector_utilization_pct": utilization,
            "sectors": deepcopy(
                sectors
            ),
        }

    def score_candidates(
        self,
        candidate_ids: list[str],
    ) -> list[dict[str, Any]]:
        with self._lock:
            candidates = []

            for candidate_id in candidate_ids:
                candidate = self._resolve_candidate(
                    candidate_id
                )

                if candidate is None:
                    raise ValueError(
                        f"Unknown candidate: "
                        f"{candidate_id}"
                    )

                candidates.append(
                    candidate
                )

            scored = public.score_candidates(
                candidates
            )

            for candidate in scored:
                key = (
                    candidate["flight_id"],
                    candidate["candidate_id"],
                )

                stress = candidate.get(
                    "stress_report",
                    {},
                )

                resilience = candidate.get(
                    "resilience_metrics",
                    {},
                )

                candidate[
                    "resilience_score"
                ] = resilience.get(
                    "future_robustness",
                    0.0,
                )

                candidate[
                    "confidence"
                ] = resilience.get(
                    "future_robustness",
                    0.0,
                )

                candidate[
                    "scenario_survival"
                ] = (
                    f"{stress.get('passed', 0)}"
                    f"/"
                    f"{stress.get('total', 0)}"
                )

                self._candidates[key] = (
                    deepcopy(candidate)
                )

            return scored

    def apply_intervention(
        self,
        candidate_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            if (
                self._resolve_candidate(
                    candidate_id
                )
                is None
            ):
                raise ValueError(
                    f"Unknown candidate: "
                    f"{candidate_id}"
                )

            return public.apply_intervention(
                candidate_id
            )

    def verify_state(
        self,
        candidate_id: str,
    ) -> dict[str, Any]:
        return public.verify_state(
            candidate_id
        )

    def advance_simulation(
        self,
        minutes: int = 1,
    ) -> dict[str, Any]:
        return public.advance_simulation(
            minutes
        )

    def reset_engine(self) -> None:
        with self._lock:
            public.reset_engine()
            self._candidates.clear()