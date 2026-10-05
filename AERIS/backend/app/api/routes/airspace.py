"""Read endpoints — airspace state, flights, disruptions, network metrics."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...engine import public as engine

router = APIRouter()


def _by_id(items: list[dict], id_key: str = "id") -> dict[str, dict]:
    """Index a list of dicts by their id_key for O(1) lookup."""
    return {item[id_key]: item for item in items}


@router.get("/airspace", summary="Full airspace snapshot")
def get_airspace():
    """Return the current full airspace state snapshot."""
    return engine.get_airspace_state()


@router.get("/flights/{flight_id}", summary="Single flight state")
def get_flight(flight_id: str):
    """Return the current state of a single flight."""
    state = engine.get_airspace_state()
    aircraft_list = state.get("aircraft", [])
    aircraft = _by_id(aircraft_list)
    if flight_id not in aircraft:
        raise HTTPException(status_code=404, detail=f"Flight {flight_id!r} not found")
    return aircraft[flight_id]


@router.get("/disruptions", summary="Active disruptions: weather cells + restrictions")
def get_disruptions():
    """Return all active weather cells and restrictions."""
    state = engine.get_airspace_state()
    return {
        "weather_cells": state.get("weather_cells", []),
        "restrictions": state.get("restrictions", []),
        "time_min": state.get("time_min", 0),
    }


@router.get("/network/metrics", summary="Aggregate network delay metrics")
def get_network_metrics():
    """Return aggregate delay and traffic metrics across the network."""
    state = engine.get_airspace_state()
    aircraft_list = state.get("aircraft", [])
    sectors_list = state.get("sectors", [])
    airports_list = state.get("airports", [])

    total_delay = sum(f.get("delay_min", 0) for f in aircraft_list)
    airborne_count = sum(1 for f in aircraft_list if f.get("status") == "AIRBORNE")
    holding_count = sum(1 for f in aircraft_list if f.get("status") == "HOLDING")

    sector_utilization = {
        s["id"]: {
            "current_traffic": s.get("current_traffic", 0),
            "capacity": s.get("capacity", 0),
            "utilization_pct": round(
                100.0 * s.get("current_traffic", 0) / max(1, s.get("capacity", 1)), 1
            ),
        }
        for s in sectors_list
    }

    return {
        "time_min": state.get("time_min", 0),
        "total_delay_min": round(total_delay, 2),
        "airborne_flights": airborne_count,
        "holding_flights": holding_count,
        "total_flights": len(aircraft_list),
        "sector_utilization": sector_utilization,
        "airports": {
            ap["id"]: {
                "arrival_capacity": ap.get("arrival_capacity"),
                "operational_status": ap.get("operational_status"),
            }
            for ap in airports_list
        },
    }
