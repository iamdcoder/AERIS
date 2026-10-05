from backend.app.engine import public


def main() -> None:
    public.reset_engine()
    public.advance_simulation(19)
    candidates = public.generate_alternatives("F102")

    print(f"Simulation time: {public.get_airspace_state()['time_min']} min")
    print("\nConstraint validation")
    for candidate in candidates:
        result = public.validate_candidate(candidate)
        status = "FEASIBLE" if result["feasible"] else "REJECTED"
        print(f"{candidate['candidate_id']}: {status}")
        if not result["feasible"]:
            for reason in result["rejection_reasons"]:
                print(f"  - {reason}")

    ranked = public.score_candidates(candidates)
    print("\nRanked feasible candidates")
    for candidate in ranked:
        if candidate["feasible"]:
            print(
                f"{candidate['candidate_id']}: score={candidate['decision_score']:.3f}, "
                f"target_delta={candidate['target_delay_min']:.2f} min, "
                f"network_delta={candidate['network_delay_delta_min']:.2f} min, "
                f"stress={candidate['stress_survival']['passed']}/{candidate['stress_survival']['total']}"
            )


if __name__ == "__main__":
    main()
