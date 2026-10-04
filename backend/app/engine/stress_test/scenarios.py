from __future__ import annotations

from copy import deepcopy


def build_stress_scenarios(state) -> list[dict]:
    profiles = state.scenario.get("stress_profiles", [])
    return [deepcopy(p) for p in profiles]


def perturb_state(state, profile: dict):
    if "weather_expand_factor" in profile:
        factor = float(profile["weather_expand_factor"])
        for cell in state.weather_cells.values():
            coords = cell.geometry["coordinates"][0]
            lons = [p[0] for p in coords]
            lats = [p[1] for p in coords]
            cx, cy = sum(lons) / len(lons), sum(lats) / len(lats)
            new_coords = [[cx + (lon - cx) * factor, cy + (lat - cy) * factor] for lon, lat in coords]
            cell.geometry = {"type": "Polygon", "coordinates": [new_coords]}

    for sid, factor in profile.get("sector_capacity_factor", {}).items():
        if sid in state.sectors:
            state.sectors[sid].capacity = max(1, int(round(state.sectors[sid].capacity * float(factor))))

    traffic_factor = profile.get("traffic_factor")
    if traffic_factor:
        for sector in state.sectors.values():
            sector.current_traffic = int(round(sector.current_traffic * float(traffic_factor)))
            sector.forecast_traffic = int(round(sector.forecast_traffic * float(traffic_factor)))

    for aid, factor in profile.get("airport_capacity_factor", {}).items():
        if aid in state.airports:
            state.airports[aid].arrival_capacity = max(1, int(round(state.airports[aid].arrival_capacity * float(factor))))

    return state
