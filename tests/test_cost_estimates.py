from packages.core.roi.cost_models import estimate, load_costs


def test_estimate():
    c = load_costs(None)
    cost = estimate(1000, 500, "openai/gpt-3.5-turbo", c)
    assert cost > 0

