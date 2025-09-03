from packages.core.routing.router import score, explain


def test_basic():
    w = {"web": 1, "agent": 1, "ask": 1, "direct": 1}
    s = score("What is the latest macOS notarization policy in 2025?", w)
    assert max(s, key=s.get) == "web"
    r = score("Implement FastAPI endpoint and Dockerfile", w)
    assert max(r, key=r.get) == "agent"

