from app.engine import public


def test_public_facade_runs_flagship_loop():
    public.reset_engine()
    public.advance_simulation(19)
    candidates = public.generate_alternatives("F102")
    scored = public.score_candidates(candidates)
    assert len(scored) == 5
    assert all("decision_score" in c for c in scored)
