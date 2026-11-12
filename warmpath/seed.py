"""Builds data/warmpath.rl from data/seed.json: a made-up owner with two brands, two agent teams,
twelve studios and the people at them, a month of outreach history and research notes.
All names are fictional."""
import json, os, sys
from . import graph
from .embed import embed

HERE = os.path.dirname(__file__)

def build(path=None, seed_file=None):
    path = os.path.abspath(path or graph.DEFAULT_DB)
    if os.path.exists(path):
        os.remove(path)
    d = json.load(open(seed_file or os.path.join(HERE, "..", "data", "seed.json")))
    with graph.connect(path) as c:
        graph.apply_schema(c)
        c.execute("UNWIND $o AS o CREATE (:Owner {key: o.key, name: o.name})", {"o": d["owners"]})
        c.execute("""UNWIND $b AS b MATCH (o:Owner {key: b.owner})
                     CREATE (o)-[:OWNS]->(:Brand {key: b.key, name: b.name, domain: b.domain})""", {"b": d["brands"]})
        c.execute("UNWIND $c AS x CREATE (:Company {key: x.key, name: x.name, country: x.country, site: x.site, kind: x.kind})", {"c": d["companies"]})
        c.execute("""UNWIND $p AS x MATCH (co:Company {key: x.company})
                     CREATE (:Person {key: x.key, name: x.name, role: x.role})-[:WORKS_AT]->(co)""", {"p": [p for p in d["people"] if p.get("company")]})
        c.execute("UNWIND $p AS x CREATE (:Person {key: x.key, name: x.name, role: x.role})", {"p": [p for p in d["people"] if not p.get("company")]})
        c.execute("""UNWIND $k AS k MATCH (a:Person {key: k[0]}), (b:Person {key: k[1]})
                     CREATE (a)-[:KNOWS {how: k[2]}]->(b)""", {"k": d["knows"]})
        c.execute("""UNWIND $t AS t MATCH (h:Person {key: t.backedBy}), (b:Brand {key: t.brand})
                     CREATE (tm:Team {key: t.key, name: t.name})-[:BACKED_BY]->(h), (tm)-[:WORKS_FOR]->(b)""", {"t": d["teams"]})
        c.execute("""UNWIND $a AS a MATCH (tm:Team {key: a.team})
                     CREATE (tm)-[:RUNS]->(:Agent {key: a.key, name: a.name, role: a.role})""", {"a": d["agents"]})
        for t in d["touches"]:
            tid = graph.log_touch(c, t["agent"], t["person"], t["brand"], t["channel"], t["text"], at=t["at"], id=t["id"])
            if t.get("reply"):
                graph.log_reply(c, tid, t["reply"]["sentiment"], t["reply"]["text"], at=t["reply"]["at"])
        for o in d["optouts"]:
            graph.opt_out(c, o["person"], o["brand"], at=o["at"])
        vecs = embed([n["text"] for n in d["notes"]])
        for n, v in zip(d["notes"], vecs):
            graph.add_note(c, n["agent"], n["company"], n["text"], v, at=n["at"], id=n["id"])
        counts = c.execute("MATCH (n) RETURN count(n) AS nodes, COUNT { MATCH ()-[r]->() RETURN r } AS rels").single()
    return path, dict(counts)

if __name__ == "__main__":
    print(build(*sys.argv[1:2]))
