from __future__ import annotations

from shapely.geometry import LineString, Polygon


def restriction_check(state, route: list[str], altitude_ft: float) -> dict:
    line = LineString([(state.graph.nodes[n]["lon"], state.graph.nodes[n]["lat"]) for n in route])
    violations = []
    for restriction in state.restrictions.values():
        active = restriction.active or (
            restriction.active_from_min <= state.time_min <= restriction.active_to_min
        )
        if not active:
            continue
        polygon = Polygon(restriction.region["coordinates"][0])
        intersects = polygon.intersects(line)
        altitude_conflict = True
        if restriction.min_altitude_ft is not None:
            altitude_conflict &= altitude_ft >= restriction.min_altitude_ft
        if restriction.max_altitude_ft is not None:
            altitude_conflict &= altitude_ft <= restriction.max_altitude_ft
        if intersects and altitude_conflict:
            violations.append({
                "restriction_id": restriction.id,
                "intersection": True,
                "altitude_conflict": True,
                "reason": restriction.reason,
            })

    return {
        "violations": violations,
        "passed": not violations,
        "violation_reason": None if not violations else violations[0]["reason"],
    }
