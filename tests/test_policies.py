from packages.core.policy.budgets import enforce


def test_enforce():
    assert enforce("observe", True) == "allow"
    assert enforce("soft", True) == "degrade"
    assert enforce("hard", True) == "deny"

