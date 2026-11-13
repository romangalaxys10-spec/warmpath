"""warmpath CLI: ask the shared graph before an agent sends anything.

  python -m warmpath check  <agent> <person> <brand>
  python -m warmpath find   <brand> "<what you are looking for>" [--country AE]
  python -m warmpath claim  <agent> <company>
  python -m warmpath sent   <agent> <person> <brand> <channel> "<text>"
  python -m warmpath optout <person> <brand>
  python -m warmpath seed   (rebuild data/warmpath.rl from data/seed.json)
  python -m warmpath demo   (the story in the video, on a scratch copy)
"""
import argparse, json, sys
from . import graph

def main(argv=None):
    ap = argparse.ArgumentParser(prog="warmpath", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=None, help="store path (default data/warmpath.rl or $WARMPATH_DB)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    x = sp.add_parser("check"); x.add_argument("agent"); x.add_argument("person"); x.add_argument("brand")
    x = sp.add_parser("find"); x.add_argument("brand"); x.add_argument("query"); x.add_argument("--country"); x.add_argument("--top", type=int, default=5)
    x = sp.add_parser("claim"); x.add_argument("agent"); x.add_argument("company"); x.add_argument("--hours", type=int, default=6)
    x = sp.add_parser("sent"); x.add_argument("agent"); x.add_argument("person"); x.add_argument("brand"); x.add_argument("channel"); x.add_argument("text")
    x = sp.add_parser("optout"); x.add_argument("person"); x.add_argument("brand")
    sp.add_parser("seed"); sp.add_parser("demo")
    a = ap.parse_args(argv)
    if a.cmd == "seed":
        from .seed import build; print(build(a.db)); return
    if a.cmd == "demo":
        from .demo import run; run(a.db); return
    with graph.connect(a.db, read_only=a.cmd in ("check", "find")) as c:
        if a.cmd == "check":
            v = graph.can_contact(c, a.agent, a.person, a.brand)
            print(json.dumps({"decision": v.decision, "reasons": v.reasons, "warm_path": v.warm_path}, indent=2))
            sys.exit(0 if v.decision == "SEND" else 2)
        if a.cmd == "find":
            from .embed import embed_one
            for r in graph.recall(c, embed_one(a.query), a.brand, country=a.country, top=a.top):
                print(json.dumps(r))
        if a.cmd == "claim":
            won, holders = graph.claim(c, a.agent, a.company, hours=a.hours)
            print(json.dumps({"won": won, "held_by": holders})); sys.exit(0 if won else 2)
        if a.cmd == "sent":
            print(graph.log_touch(c, a.agent, a.person, a.brand, a.channel, a.text))
        if a.cmd == "optout":
            graph.opt_out(c, a.person, a.brand); print("ok")

if __name__ == "__main__":
    main()
