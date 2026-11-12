import os, shutil, tempfile, pytest
from warmpath import graph

NOW = "2026-11-13T09:00:00Z"

@pytest.fixture
def c():
    src = os.path.join(os.path.dirname(__file__), "..", "data", "warmpath.rl")
    tmp = os.path.join(tempfile.mkdtemp(), "t.rl")
    shutil.copy(src, tmp)
    conn = graph.connect(tmp)
    yield conn
    conn.close()

def test_colleague_touched_by_other_team_holds(c):
    assert graph.can_contact(c, "writer-a", "omar", "qa", now=NOW).decision == "HOLD"

def test_optout_covers_sister_brand(c):
    assert graph.can_contact(c, "writer-a", "karim", "qa", now=NOW).decision == "BLOCK"

def test_refusal_blocks_whole_company(c):
    assert graph.can_contact(c, "writer-a", "sofia", "qa", now=NOW).decision == "BLOCK"

def test_warm_path_found(c):
    v = graph.can_contact(c, "writer-a", "noah", "qa", now=NOW)
    assert v.decision == "SEND" and v.warm_path[-1] == "Noah Tremblay"

def test_old_touch_past_cooldown_sends(c):
    assert graph.can_contact(c, "writer-a", "liam", "qa", now=NOW).decision == "SEND"

def test_claim_is_exclusive(c):
    assert graph.claim(c, "scout-a", "dunelab", now=NOW) == (True, [])
    assert graph.claim(c, "scout-b", "dunelab", now=NOW) == (False, ["Scout-A"])
    assert graph.can_contact(c, "writer-b", "yusuf", "host", now=NOW).decision == "HOLD"

def test_send_then_other_team_holds(c):
    graph.log_touch(c, "writer-a", "ethan", "qa", "email", "hi", at=NOW, id="x")
    assert graph.can_contact(c, "writer-b", "ethan", "host", now=NOW).decision == "HOLD"

def test_unknown_person_blocks(c):
    assert graph.can_contact(c, "writer-a", "nobody", "qa", now=NOW).decision == "BLOCK"
