from __future__ import annotations

from shapely.geometry import LineString, Polygon


def _route_line(state, route: list[str]) -> LineString:
    return LineString([(state.graph.nodes[n]["lon"], state.graph.nodes[n]["lat"]) for n in route])


def weather_intersection(state, route: list[str]) -> dict:
    line = _route_line(state, route)
    affected = []
    max_severity = "NONE"
    rank = {"NONE": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3, "SEVERE": 4}

    for cell in state.weather_cells.values():
        if not cell.active:
            continue
        polygon = Polygon(cell.geometry["coordinates"][0])
        if polygon.intersects(line):
            intersection = polygon.intersection(line)
            severity = cell.intensity.upper()
            if rank.get(severity, 0) > rank.get(max_severity, 0):
                max_severity = severity
            affected.append({
                "weather_id": cell.id,
                "intersection_length": round(float(intersection.length), 4),
                "severity": severity,
            })

    severity = max_severity
    bypass = severity in {"HIGH", "SEVERE"}
    return {
        "intersects": bool(affected),
        "severity": severity,
        "affected_segments": affected,
        "bypass_implication": "RECOMMENDED" if bypass else "OPTIONAL",
        "passed": True,
    }
