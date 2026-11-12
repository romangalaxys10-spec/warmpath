"""Every read and write the agents make. Each function is one Cypher statement (or a short transaction)."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
import relate

DEFAULT_DB = os.environ.get("WARMPATH_DB", os.path.join(os.path.dirname(__file__), "..", "data", "warmpath.rl"))
COOLDOWN_DAYS = 30

def connect(path: str | None = None, read_only: bool = False):
    return relate.connect(os.path.abspath(path or DEFAULT_DB), read_only=read_only)

def apply_schema(conn):
    text = open(os.path.join(os.path.dirname(__file__), "schema.cypher")).read()
    for stmt in [s.strip() for s in text.split(";") if s.strip()]:
        conn.execute(stmt)

def first(cur):
    """First row of a result, or None (single() raises on zero rows)."""
    for row in cur:
        return row
    return None

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ---------------------------------------------------------------- the gate
@dataclass
class Verdict:
    decision: str                  # SEND | HOLD | BLOCK
    reasons: list = field(default_factory=list)
    warm_path: list | None = None

GATE = """
MATCH (p:Person {key: $person})-[:WORKS_AT]->(c:Company)
MATCH (b:Brand {key: $brand})<-[:OWNS]-(o:Owner)
OPTIONAL MATCH (p)-[oo:OPTED_OUT]->(ob:Brand)<-[:OWNS]-(o)
WITH p, c, b, o, collect(DISTINCT {brand: ob.name, at: toString(oo.at)}) AS optouts
CALL (c, o) {
  OPTIONAL MATCH (a:Agent)-[:SENT]->(t:Touch)-[:TO]->(q:Person)-[:WORKS_AT]->(c),
                 (t)-[:FOR]->(tb:Brand)<-[:OWNS]-(o), (a)<-[:RUNS]-(tm:Team)
  WHERE t.at >= datetime($now) - duration({days: $cooldown})
  RETURN collect(DISTINCT {who: q.name, agent: a.name, team: tm.name, brand: tb.name,
                           channel: t.channel, at: toString(t.at)}) AS recent
}
CALL (c) {
  OPTIONAL MATCH (r:Reply {sentiment: 'no'})-[:ANSWERS]->(:Touch)-[:TO]->(:Person)-[:WORKS_AT]->(c)
  RETURN collect(DISTINCT r.text) AS refusals
}
CALL (c) {
  OPTIONAL MATCH (other:Agent)-[cl:CLAIMED]->(c) WHERE other.key <> $agent AND cl.until > datetime($now)
  RETURN collect(DISTINCT other.name) AS claimedBy
}
RETURN p.name AS person, c.name AS company,
       [x IN optouts WHERE x.brand IS NOT NULL] AS optouts, [x IN recent WHERE x.who IS NOT NULL] AS recent,
       refusals, claimedBy
"""

WARM = """
MATCH (me:Agent {key: $agent})<-[:RUNS]-(:Team)-[:BACKED_BY]->(h:Person)
MATCH (target:Person {key: $person})
MATCH path = SHORTEST 1 (h)-[:KNOWS|WORKS_AT]-{1,4}(target)
RETURN [n IN nodes(path) | coalesce(n.name, n.key)] AS hops,
       [r IN relationships(path) | type(r)] AS rels, length(path) AS len
ORDER BY len LIMIT 1
"""

def can_contact(conn, agent: str, person: str, brand: str, now: str | None = None) -> Verdict:
    now = now or now_iso()
    row = first(conn.execute(GATE, {"person": person, "brand": brand, "agent": agent,
                              "now": now, "cooldown": COOLDOWN_DAYS}))
    if row is None:
        return Verdict("BLOCK", ["unknown person or brand"])
    v = Verdict("SEND")
    for o in row["optouts"]:
        v.decision = "BLOCK"
        v.reasons.append(f"{row['person']} opted out via {o['brand']} on {o['at'][:10]}; the opt-out covers every brand of the same owner")
    for r in row["refusals"]:
        v.decision = "BLOCK"
        v.reasons.append(f"{row['company']} already said no: \"{r}\"")
    if v.decision != "BLOCK":
        for t in row["recent"]:
            v.decision = "HOLD"
            v.reasons.append(f"{t['who']} at {row['company']} got {'an' if t['channel'][0].lower() in 'aeiou' else 'a'} {t['channel']} from {t['agent']} ({t['team']}, {t['brand']}) on {t['at'][:10]}")
        for a in row["claimedBy"]:
            v.decision = "HOLD"
            v.reasons.append(f"{a} has claimed {row['company']} and is working it now")
    if v.decision == "SEND":
        w = first(conn.execute(WARM, {"agent": agent, "person": person}))
        if w and w["len"] >= 2:
            v.warm_path = list(w["hops"])
            v.reasons.append("warm intro: " + " -> ".join(w["hops"]))
        else:
            v.reasons.append("no one has touched this company in 30 days and nobody opted out")
    return v

# ---------------------------------------------------------------- claims (two agents, one prospect)
CLAIM = """
MATCH (a:Agent {key: $agent}), (c:Company {key: $company})
OPTIONAL MATCH (other:Agent)-[cl:CLAIMED]->(c) WHERE other <> a AND cl.until > datetime($now)
WITH a, c, collect(other.name) AS holders
CALL (a, c, holders) {
  WITH a, c, holders WHERE size(holders) = 0
  MERGE (a)-[cl:CLAIMED]->(c)
  SET cl.at = datetime($now), cl.until = datetime($now) + duration({hours: $hours})
  RETURN true AS won
  UNION
  WITH holders WHERE size(holders) > 0
  RETURN false AS won
}
RETURN won, holders
"""

def claim(conn, agent, company, hours=6, now=None):
    r = conn.execute(CLAIM, {"agent": agent, "company": company, "now": now or now_iso(), "hours": hours}).single()
    return bool(r["won"]), list(r["holders"])

# ---------------------------------------------------------------- writes
LOG_TOUCH = """
MATCH (a:Agent {key: $agent}), (p:Person {key: $person}), (b:Brand {key: $brand})
CREATE (a)-[:SENT]->(t:Touch {id: $id, channel: $channel, at: datetime($at), text: $text})-[:TO]->(p),
       (t)-[:FOR]->(b)
RETURN t.id AS id
"""
def log_touch(conn, agent, person, brand, channel, text, at=None, id=None):
    at = at or now_iso()
    id = id or f"t-{agent}-{person}-{at}"
    return conn.execute(LOG_TOUCH, {"agent": agent, "person": person, "brand": brand, "channel": channel,
                                    "text": text, "at": at, "id": id}).single()["id"]

def log_reply(conn, touch_id, sentiment, text, at=None):
    conn.execute("""MATCH (t:Touch {id: $tid})-[:TO]->(p:Person)
                    CREATE (r:Reply {at: datetime($at), sentiment: $s, text: $text})-[:ANSWERS]->(t)""",
                 {"tid": touch_id, "s": sentiment, "text": text, "at": at or now_iso()})

def opt_out(conn, person, brand, at=None):
    conn.execute("""MATCH (p:Person {key: $p}), (b:Brand {key: $b})
                    MERGE (p)-[o:OPTED_OUT]->(b) ON CREATE SET o.at = datetime($at)""",
                 {"p": person, "b": brand, "at": at or now_iso()})

def add_note(conn, agent, company, text, embedding, at=None, id=None):
    at = at or now_iso()
    conn.execute("""MATCH (a:Agent {key: $agent}), (c:Company {key: $company})
                    CREATE (a)-[:WROTE]->(n:Note {id: $id, text: $text, at: datetime($at),
                                                  embedding: vector($e, 384, FLOAT32)})-[:ABOUT]->(c)""",
                 {"agent": agent, "company": company, "text": text, "at": at, "e": embedding,
                  "id": id or f"n-{company}-{at}"})

# ---------------------------------------------------------------- hybrid recall: meaning + graph
RECALL = """
MATCH (n:Note)
SEARCH n IN (VECTOR INDEX note_embedding FOR $q LIMIT $k) SCORE AS score
MATCH (n)-[:ABOUT]->(c:Company)
WHERE $country IS NULL OR c.country = $country
MATCH (b:Brand {key: $brand})<-[:OWNS]-(o:Owner)
WITH c, max(score) AS score, collect(n.text)[0] AS why, o
WHERE NOT EXISTS {
        MATCH (t:Touch)-[:TO]->(:Person)-[:WORKS_AT]->(c) WHERE t.at >= datetime($now) - duration({days: $cooldown}) }
  AND NOT EXISTS { MATCH (pp:Person)-[:WORKS_AT]->(c), (pp)-[:OPTED_OUT]->(:Brand)<-[:OWNS]-(o) }
  AND NOT EXISTS { MATCH (:Reply {sentiment: 'no'})-[:ANSWERS]->(:Touch)-[:TO]->(:Person)-[:WORKS_AT]->(c) }
RETURN c.key AS key, c.name AS company, c.country AS country, round(score, 3) AS score, why
ORDER BY score DESC LIMIT $top
"""

def recall(conn, question_vec, brand, country=None, top=5, k=40, now=None):
    return [dict(r) for r in conn.execute(RECALL, {"q": question_vec, "k": k, "brand": brand, "country": country,
                                                   "top": top, "now": now or now_iso(), "cooldown": COOLDOWN_DAYS})]
