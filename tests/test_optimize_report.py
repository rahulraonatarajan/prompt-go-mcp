from packages.core.roi.optimizer import downshift_savings


def test_savings():
    s = downshift_savings([(1000, 500, 1.00), (2000, 1000, 2.00)], cheaper_ratio=0.5)
    assert s > 0

