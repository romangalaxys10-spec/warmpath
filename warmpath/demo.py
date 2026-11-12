"""The story in the demo video, run against a scratch copy of data/warmpath.rl.
Two agent teams sell two brands of the same owner. Without shared memory they would
message the same studios. With one Relate graph, every send goes through the gate."""
import os, shutil, tempfile
from . import graph
from .embed import embed_one

NOW = "2026-11-13T09:00:00Z"
ICON = {"SEND": "SEND ", "HOLD": "HOLD ", "BLOCK": "BLOCK"}

def run(src=None):
    src = os.path.abspath(src or graph.DEFAULT_DB)
    tmp = os.path.join(tempfile.mkdtemp(), "demo.rl")
    shutil.copy(src, tmp)
    c = graph.connect(tmp)
    print("\n1. Scout-A asks the graph for studios that fit Northlight QA, by meaning, minus anyone touched, refused or opted out")
    q = embed_one("studios that build web apps with payment and signup forms")
    for r in graph.recall(c, q, "qa", now=NOW, top=5):
        print(f"   {r['score']:.3f}  {r['company']:<22} {r['country']}  {r['why']}")
    print("\n2. Writer-A wants to message five people. Every send goes through the gate")
    for person in ["omar", "karim", "sofia", "noah", "ethan"]:
        v = graph.can_contact(c, "writer-a", person, "qa", now=NOW)
        print(f"   {ICON[v.decision]}  {person:<6} {v.reasons[0]}")
    print("\n3. Both scouts reach for Dune Lab at the same moment")
    print("   Scout-A claim:", graph.claim(c, "scout-a", "dunelab", now=NOW))
    print("   Scout-B claim:", graph.claim(c, "scout-b", "dunelab", now=NOW))
    print("\n4. Writer-A sends to Ethan. Then Team B's writer tries Harborstack for the other brand")
    graph.log_touch(c, "writer-a", "ethan", "qa", "email", "Ethan, Harborstack's portals have login, billing and uploads...", at=NOW, id="demo-1")
    v = graph.can_contact(c, "writer-b", "ethan", "host", now=NOW)
    print(f"   {ICON[v.decision]}  {v.reasons[0]}")
    print("\n5. Ethan replies 'please stop'. One opt-out, and it covers both brands")
    graph.opt_out(c, "ethan", "qa", at=NOW)
    v = graph.can_contact(c, "writer-b", "ethan", "host", now="2026-12-20T09:00:00Z")
    print(f"   {ICON[v.decision]}  {v.reasons[0]}")
    c.close()

if __name__ == "__main__":
    run()
