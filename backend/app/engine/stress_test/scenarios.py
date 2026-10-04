from __future__ import annotations

from copy import deepcopy
import math


def build_stress_scenarios(state) -> list[dict]:
    """Validate and return deep copies of stress profiles defined in the scenario."""
    profiles = state.scenario.get("stress_profiles", [])
    seen_ids = set()
    validated = []
    for p in profiles:
        if not isinstance(p, dict):
            raise ValueError("Stress profile must be a dictionary")
        pid = p.get("id")
        name = p.get("name")
        if not pid or not isinstance(pid, str):
            raise ValueError("Stress profile must have a valid string 'id'")
        if not name or not isinstance(name, str):
            raise ValueError("Stress profile must have a valid string 'name'")
        if pid in seen_ids:
            raise ValueError(f"Duplicate stress profile id: {pid}")
        seen_ids.add(pid)
        validated.append(deepcopy(p))
    return validated


def perturb_state(state, profile: dict):
    """Apply stress perturbations to a cloned WorldState."""
    new_state = state.clone()

    if "weather_expand_factor" in profile:
        factor_raw = profile["weather_expand_factor"]
        try:
            factor = float(factor_raw)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid weather_expand_factor: {factor_raw}")
        if not math.isfinite(factor) or factor <= 0:
            raise ValueError(f"weather_expand_factor must be finite and > 0, got {factor}")

        for cell in new_state.weather_cells.values():
            coords = cell.geometry["coordinates"][0]
            lons = [p[0] for p in coords]
            lats = [p[1] for p in coords]
            cx, cy = sum(lons) / len(lons), sum(lats) / len(lats)
            new_coords = [[cx + (lon - cx) * factor, cy + (lat - cy) * factor] for lon, lat in coords]
            if new_coords and new_coords[0] != new_coords[-1]:
                new_coords[-1] = list(new_coords[0])
            cell.geometry = {"type": "Polygon", "coordinates": [new_coords]}

    if "sector_capacity_factor" in profile:
        sec_factors = profile["sector_capacity_factor"]
        if not isinstance(sec_factors, dict):
            raise ValueError("sector_capacity_factor must be a dict")
        for sid, factor_raw in sec_factors.items():
            try:
                factor = float(factor_raw)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid sector_capacity_factor for {sid}: {factor_raw}")
            if not math.isfinite(factor) or factor <= 0:
                raise ValueError(f"sector_capacity_factor for {sid} must be finite and > 0, got {factor}")
            if sid in new_state.sectors:
                old_cap = new_state.sectors[sid].capacity
                new_state.sectors[sid].capacity = max(1, int(round(old_cap * factor)))

    if "traffic_factor" in profile:
        traffic_raw = profile["traffic_factor"]
        try:
            traffic_factor = float(traffic_raw)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid traffic_factor: {traffic_raw}")
        if not math.isfinite(traffic_factor) or traffic_factor <= 0:
            raise ValueError(f"traffic_factor must be finite and > 0, got {traffic_factor}")

        for sector in new_state.sectors.values():
            sector.current_traffic = max(0, int(round(sector.current_traffic * traffic_factor)))
            sector.forecast_traffic = max(0, int(round(sector.forecast_traffic * traffic_factor)))

    if "airport_capacity_factor" in profile:
        air_factors = profile["airport_capacity_factor"]
        if not isinstance(air_factors, dict):
            raise ValueError("airport_capacity_factor must be a dict")
        for aid, factor_raw in air_factors.items():
            try:
                factor = float(factor_raw)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid airport_capacity_factor for {aid}: {factor_raw}")
            if not math.isfinite(factor) or factor <= 0:
                raise ValueError(f"airport_capacity_factor for {aid} must be finite and > 0, got {factor}")
            if aid in new_state.airports:
                old_cap = new_state.airports[aid].arrival_capacity
                new_state.airports[aid].arrival_capacity = max(1, int(round(old_cap * factor)))

    if "activate_restrictions" in profile:
        # Support activating new/future temporary restrictions absent in the base world.
        restriction_ids = profile["activate_restrictions"]
        if not isinstance(restriction_ids, list):
            raise ValueError("activate_restrictions must be a list of restriction_id strings")
        for rid in restriction_ids:
            if not isinstance(rid, str):
                raise ValueError(f"activate_restrictions entries must be strings, got {rid!r}")
            if rid in new_state.restrictions:
                new_state.restrictions[rid].active = True
            # If the restriction doesn't exist in this world snapshot, silently skip —
            # it may be a future restriction that isn't loaded in the base dataset.

    return new_state
