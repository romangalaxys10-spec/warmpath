# Warm Path

**One shared graph memory that stops a team of outreach agents from stepping on each other.**

Small companies now run several AI agents at once: one finds prospects, one writes, one sends, sometimes a second team sells a sister brand over another channel. Each agent keeps its own notes. So the same studio gets an email from one agent on Monday and a WhatsApp from another on Tuesday, a person who said "stop" to one brand hears from the other, and nobody notices that the founder already knows someone there.

Warm Path puts every agent on one [Relate](https://relatedb.ai) graph. Before any agent sends, it asks the graph one question, and gets back `SEND`, `HOLD` or `BLOCK` with the reason in plain words:

```
HOLD   omar   Lina Saeed at Pixelforge Studio got a WhatsApp from Writer-B (Team B (WhatsApp), Northlight Hosting) on 2026-11-05
BLOCK  karim  Karim Aziz opted out via Northlight Hosting on 2026-11-03; the opt-out covers every brand of the same owner
BLOCK  sofia  Palmcode already said no: "Not interested, we have an in-house QA team."
SEND   noah   warm intro: Roman (founder) -> Maya (partner) -> Zoe Martin -> Noah Tremblay
SEND   ethan  no one has touched this company in 30 days and nobody opted out
```

Every one of those answers needs connected context: a colleague at the same company, a brand owned by the same owner, a reply to a message another agent sent, a friend of a friend. That is a graph question, and Relate answers it in one Cypher statement, in-process, from one file.

## Run it (about 2 minutes)

Needs Python 3.10+ on macOS or Linux.

```bash
git clone <this repo> warmpath && cd warmpath
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m warmpath demo          # the five-step story from the video
pytest -q                        # 8 tests
```

The first run downloads a small local embedding model (BAAI/bge-small-en-v1.5, ~65 MB). No API keys, no server, no account.

Try it yourself:

```bash
python -m warmpath check writer-a noah qa                       # SEND, with the warm intro path
python -m warmpath check writer-a karim qa                      # BLOCK, opted out of the sister brand
python -m warmpath find qa "studios with payment and signup forms" --country CA
python -m warmpath claim scout-a dunelab && python -m warmpath claim scout-b dunelab
```

`check` and `claim` exit 0 on go and 2 on hold/block, so any agent framework can call them as a tool.

### Give the graph to Claude Code (or any MCP host)

Install the Relate CLI (`curl -sSfL https://relatedb.ai/install.sh | bash`), then use `mcp/claude_code.json`:

```bash
relate serve --mcp stdio --database ./data/warmpath.rl --read-only
```

The agent gets `read_cypher` and `get_schema` on the same store and can ask its own questions, for example "who opted out of anything this owner sells?":

```cypher
MATCH (p:Person)-[:OPTED_OUT]->(b:Brand)<-[:OWNS]-(o:Owner)-[:OWNS]->(other:Brand)
RETURN p.name AS person, b.name AS optedOutOf, collect(other.name) AS coveredBrands
```

## How it uses Relate

| | |
|---|---|
| **Mode** | Embedded, single-file store (`data/warmpath.rl`) through the Python package `relate-db`, plus `relate serve --mcp` over the same file. Agents run in-process, so the gate check costs well under a millisecond and there is nothing to deploy. One file means a team can copy, version or hand over its whole outreach memory. |
| **Where data lives** | `data/warmpath.rl`, committed in this repo and rebuilt from `data/seed.json` with `python -m warmpath seed`. The demo and tests work on a scratch copy, so the committed store never changes. |
| **Hybrid retrieval** | `find` runs a vector search over research notes (`VECTOR INDEX note_embedding`, 384-d, cosine) and in the same statement walks the graph to drop any company that was touched in the last 30 days, said no, or has anyone who opted out of the owner's brands. Meaning and relationships in one query. |
| **Paths** | The warm intro is `SHORTEST 1 (h)-[:KNOWS|WORKS_AT]-{1,4}(target)` from the human behind the agent's team. |
| **Coordination** | `claim` writes a time-boxed `CLAIMED` edge, so two scouts never research the same company at once. |
| **Constraints** | Unique keys on every entity, so agents `MERGE` into the same nodes instead of creating duplicates. |

### The graph

```
(:Owner)-[:OWNS]->(:Brand)<-[:WORKS_FOR]-(:Team)-[:RUNS]->(:Agent)
(:Team)-[:BACKED_BY]->(:Person)                      the human behind the team
(:Person)-[:WORKS_AT]->(:Company)    (:Person)-[:KNOWS]->(:Person)
(:Agent)-[:SENT]->(:Touch)-[:TO]->(:Person)   (:Touch)-[:FOR]->(:Brand)
(:Reply {sentiment})-[:ANSWERS]->(:Touch)
(:Person)-[:OPTED_OUT {at}]->(:Brand)
(:Agent)-[:WROTE]->(:Note {text, embedding})-[:ABOUT]->(:Company)
(:Agent)-[:CLAIMED {until}]->(:Company)
```

The gate (`warmpath/graph.py`, `GATE`) is one statement with three `CALL` subqueries: recent touches by any agent of the same owner to anyone at the company, refusals from anyone at the company, and live claims by other agents.

## Files

- `warmpath/graph.py`: every read and write the agents make, each one Cypher statement
- `warmpath/schema.cypher`: constraints, index and vector index
- `warmpath/seed.py`, `data/seed.json`: the example world (all names and companies are made up)
- `warmpath/demo.py`: the story in the video
- `warmpath/cli.py`: the commands above
- `tests/test_gate.py`: 8 tests, one per rule

## Built with AI

Disclosed per the rules: the code, README and demo video were written with the help of AI coding assistants. The idea comes from a real problem we hit running several outreach agents for our own products. The project was started on 13 November 2026, for the Relate hackathon.

## License

MIT
