from copy import deepcopy
from typing import Any

from .loader import load_fixture


class MockEngineClient:
    """
    Fixture-backed engine adapter for unit tests and offline demos.

    Production Copilot defaults use RealEngineClient instead.
    """

    def __init__(self) -> None:
        self._state = load_fixture(
            "state.json"
        )

        self._alternatives = load_fixture(
            "alternatives.json"
        )

        self._simulations = load_fixture(
            "simulations.json"
        )

        self._stress_tests = load_fixture(
            "stress_tests.json"
        )

    def get_state(
        self,
    ) -> dict[str, Any]:
        return deepcopy(
            self._state
        )

    def get_airspace_state(self) -> dict[str, Any]:
        return self.get_state()

    def get_disruptions(
        self,
    ) -> list[dict[str, Any]]:
        return deepcopy(
            self._state.get(
                "alerts",
                [],
            )
        )

    def get_target_flight(
        self,
        flight_id: str,
    ) -> dict[str, Any] | None:
        flight = self._state.get(
            "target_flight"
        )

        if not flight:
            return None

        if flight.get(
            "id"
        ) != flight_id:
            return None

        return deepcopy(
            flight
        )

    def get_sector_state(
        self,
        sector_id: str,
    ) -> dict[str, Any] | None:
        for sector in self._state.get(
            "sectors",
            [],
        ):
            if sector.get(
                "id"
            ) == sector_id:
                return deepcopy(
                    sector
                )

        return None

    def get_airport_state(
        self,
        airport_id: str,
    ) -> dict[str, Any] | None:
        for airport in self._state.get(
            "airports",
            [],
        ):
            if airport.get(
                "id"
            ) == airport_id:
                return deepcopy(
                    airport
                )

        return None

    def get_weather_state(self) -> list[dict[str, Any]]:
        return deepcopy(self._state.get("weather_cells", []))

    def get_restrictions(self) -> list[dict[str, Any]]:
        return deepcopy(self._state.get("restrictions", []))

    def get_network_metrics(
        self,
    ) -> dict[str, Any]:
        summary = self._state.get(
            "network_summary",
            {},
        )

        return deepcopy(
            summary
        )

    def get_alternatives(
        self,
        flight_id: str,
    ) -> list[dict[str, Any]]:
        alternatives = self._alternatives.get(
            "alternatives",
            [],
        )

        return deepcopy(
            [
                item
                for item in alternatives
                if item.get("flight_id")
                in (None, flight_id)
            ]
        )

    def get_candidate(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None:
        for candidate in self._alternatives.get(
            "alternatives",
            [],
        ):
            if (
                candidate.get("candidate_id")
                == candidate_id
            ):
                return deepcopy(
                    candidate
                )

        return None

    def validate_candidate(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None:
        candidate = self.get_candidate(
            candidate_id
        )

        if candidate is None:
            return None

        return deepcopy(
            {
                "candidate_id": candidate_id,
                "feasible": candidate.get(
                    "feasible",
                    False,
                ),
                "constraint_results": candidate.get(
                    "constraint_results",
                    {},
                ),
                "rejection_reasons": candidate.get(
                    "rejection_reasons",
                    [],
                ),
                "fuel_margin_kg": candidate.get(
                    "fuel_margin_kg"
                ),
                "peak_sector_utilization": candidate.get(
                    "peak_sector_utilization"
                ),
            }
        )

    def get_simulation_results(
        self,
        candidate_ids: list[str],
    ) -> list[dict[str, Any]]:
        results = self._simulations.get(
            "results",
            [],
        )

        allowed = set(
            candidate_ids
        )

        return deepcopy(
            [
                item
                for item in results
                if item.get("candidate_id")
                in allowed
            ]
        )

    def get_simulation_result(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None:
        for result in self._simulations.get(
            "results",
            [],
        ):
            if (
                result.get("candidate_id")
                == candidate_id
            ):
                return deepcopy(
                    result
                )

        return None

    def get_stress_results(
        self,
        candidate_ids: list[str],
    ) -> list[dict[str, Any]]:
        results = self._stress_tests.get(
            "results",
            [],
        )

        allowed = set(
            candidate_ids
        )

        return deepcopy(
            [
                item
                for item in results
                if item.get("candidate_id")
                in allowed
            ]
        )

    def get_stress_result(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None:
        for result in self._stress_tests.get(
            "results",
            [],
        ):
            if (
                result.get("candidate_id")
                == candidate_id
            ):
                return deepcopy(
                    result
                )

        return None

    def get_stress_test_result(
        self,
        candidate_id: str,
    ) -> dict[str, Any] | None:
        return self.get_stress_result(candidate_id)

    def score_candidates(self, candidate_ids: list[str]) -> list[dict[str, Any]]:
        allowed = set(candidate_ids)
        return deepcopy(
            sorted(
                [
                    candidate
                    for candidate in self._alternatives.get("alternatives", [])
                    if candidate.get("candidate_id") in allowed
                ],
                key=lambda candidate: candidate.get("decision_score", 0.0),
                reverse=True,
            )
        )

    def healthcheck(
        self,
    ) -> dict[str, Any]:
        return {
            "status": "ok",
            "mode": "mock",
            "deterministic": True,
            "fixtures": 4,
        }