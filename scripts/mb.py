#!/usr/bin/env python
"""
mb.py - guarded Metabase client for the Refrens product-docs repo.

Everything we do against Metabase goes through here. The point is that the
safety rules live in code, not in prose that can be argued out of.

Reads METABASE_URL and METABASE_API_KEY from ./.env by name. Never prints them.

Commands
  env                                  show host + whether the key loaded (no values)
  sync   [--dbs 2,4]                   refresh docs/data/cache/ from the API
  dbs                                  list databases (from cache)
  tables <db> [pattern]                list collections/tables (from cache)
  fields <db> <table> [pattern]        list field paths + types + indexed (from cache)
  indexes <db> <table>                 indexed fields only (from cache)
  cards  <search>                      search saved questions (live, READ ONLY)
  card   <id>                          dump one saved question's query (live, READ ONLY)
  check  --db N --file q.json [--collection name]      guardrails only, no execution
  run    --db N --file q.json [--collection name] [--max-rows N] [--probe]
  save   --db N --file q.json --name "..." --collection-id N [--display table]

Exit code 2 means a guardrail blocked the query.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "docs", "data", "cache")
DEFAULT_MAX_ROWS = 2000
DEFAULT_TIMEOUT = 120

# Collections that are firehoses: a date range is mandatory, no exceptions.
FIREHOSE = {
    "axiosrequests", "logs", "activities", "notifications", "feeds",
    "invoiceaudits", "salesactivities", "contactactivities", "contactActivities",
    "leadpipelinehistories", "outboundcalls", "calls",
}
# Saturn tables that are never queried casually.
SQL_DENY = {
    "query_performance_logs", "pg_stat_statements", "pg_stat_statements_info",
    "pg_buffercache", "job_run_details",
}
MONGO_FORBIDDEN = ["$out", "$merge", "$where", "$function", "$accumulator"]
SQL_FORBIDDEN = r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|vacuum|reindex)\b"


# ---------------------------------------------------------------- environment

def load_env():
    path = os.path.join(ROOT, ".env")
    env = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", line)
                if m:
                    env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    url = env.get("METABASE_URL", "").rstrip("/")
    key = env.get("METABASE_API_KEY", "")
    if not url or not key:
        sys.exit("ERROR: METABASE_URL / METABASE_API_KEY not found in .env")
    return url, key


def api(path, method="GET", body=None, timeout=DEFAULT_TIMEOUT, attempts=3):
    """One HTTP call. The Azure front end in front of Metabase resets connections
    now and then, so transient failures are retried. HTTP errors are not."""
    url, key = load_env()
    data = json.dumps(body).encode("utf-8") if body is not None else None
    last = None
    for attempt in range(attempts):
        req = urllib.request.Request(url + path, data=data, method=method)
        req.add_header("x-api-key", key)
        req.add_header("User-Agent", "refrens-mb-cli/1.0")
        req.add_header("Accept", "application/json")
        req.add_header("Connection", "close")
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as fh:
                return json.loads(fh.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:600]
            sys.exit("ERROR: HTTP %s on %s\n%s" % (e.code, path, detail))
        except Exception as e:
            last = e
            if attempt < attempts - 1:
                time.sleep(2 * (attempt + 1))
    sys.exit("ERROR: %s on %s (after %d attempts)" % (last, path, attempts))


def base_url():
    return load_env()[0]


# --------------------------------------------------------------------- cache

def cache_path(name):
    return os.path.join(CACHE, name)


def read_tsv(name):
    path = cache_path(name)
    if not os.path.exists(path):
        sys.exit("ERROR: %s missing. Run: python scripts/mb.py sync" % path)
    rows = []
    with open(path, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            if line.strip():
                rows.append(dict(zip(header, line.rstrip("\n").split("\t"))))
    return rows


def write_tsv(name, header, rows):
    os.makedirs(CACHE, exist_ok=True)
    with open(cache_path(name), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(header) + "\n")
        for r in rows:
            fh.write("\t".join("" if c is None else str(c).replace("\t", " ") for c in r) + "\n")
    print("wrote %s (%d rows)" % (name, len(rows)))


def cmd_sync(args):
    ids = [int(x) for x in args.dbs.split(",")] if args.dbs else [2, 4]
    dbs = api("/api/database")
    dbs = dbs.get("data", dbs) if isinstance(dbs, dict) else dbs
    write_tsv("databases.tsv", ["id", "name", "engine"],
              [(d["id"], d["name"], d["engine"]) for d in sorted(dbs, key=lambda x: x["id"])])

    cols = api("/api/collection")
    cols = cols.get("data", cols) if isinstance(cols, dict) else cols
    write_tsv("collections.tsv", ["id", "name", "location", "can_write", "personal_owner_id"],
              [(c.get("id"), c.get("name"), c.get("location"), c.get("can_write"),
                c.get("personal_owner_id")) for c in cols])

    tables_rows, field_rows = [], []
    for db_id in ids:
        print("syncing database %d ..." % db_id)
        meta = api("/api/database/%d/metadata" % db_id, timeout=300)
        engine = meta.get("engine")
        for t in meta.get("tables", []):
            tname = t["name"] if engine == "mongo" else "%s.%s" % (t.get("schema"), t["name"])
            fields = t.get("fields", [])
            tables_rows.append((db_id, engine, tname, len(fields),
                                (t.get("description") or "").replace("\n", " ")))
            for f in fields:
                nfc = f.get("nfc_path")
                path = ".".join(nfc) if nfc else f["name"]
                field_rows.append((db_id, tname, path, f.get("database_type"),
                                   f.get("base_type"), f.get("semantic_type") or "",
                                   "Y" if f.get("database_indexed") else ""))
    write_tsv("tables.tsv", ["db", "engine", "table", "field_count", "description"], tables_rows)
    write_tsv("fields.tsv",
              ["db", "table", "path", "db_type", "base_type", "semantic_type", "indexed"],
              field_rows)
    print("done. Check docs/data/metabase-map.md for anything that changed.")


def cmd_dbs(args):
    for r in read_tsv("databases.tsv"):
        print("%-4s %-20s %s" % (r["id"], r["name"], r["engine"]))


def cmd_tables(args):
    pat = args.pattern.lower() if args.pattern else None
    for r in read_tsv("tables.tsv"):
        if r["db"] != str(args.db):
            continue
        if pat and pat not in r["table"].lower():
            continue
        print("%-40s %5s fields  %s" % (r["table"], r["field_count"], r["description"][:60]))


def _fields_for(db, table):
    return [r for r in read_tsv("fields.tsv") if r["db"] == str(db) and r["table"] == table]


def cmd_fields(args):
    rows = _fields_for(args.db, args.table)
    if not rows:
        sys.exit("ERROR: no cached fields for db %s table '%s'. Check the name with: "
                 "python scripts/mb.py tables %s %s" % (args.db, args.table, args.db, args.table))
    pat = args.pattern.lower() if args.pattern else None
    shown = 0
    for r in rows:
        if pat and pat not in r["path"].lower():
            continue
        print("%-55s %-12s %-22s %s" % (r["path"], r["db_type"], r["base_type"],
                                        "INDEXED" if r["indexed"] else ""))
        shown += 1
    print("-- %d of %d fields" % (shown, len(rows)))


def cmd_indexes(args):
    rows = [r for r in _fields_for(args.db, args.table) if r["indexed"]]
    if not rows:
        print("no indexed fields recorded for %s (db %s)" % (args.table, args.db))
        return
    for r in rows:
        print("%-45s %s" % (r["path"], r["db_type"]))


def cmd_cards(args):
    q = urllib.parse.quote(args.search)
    res = api("/api/search?q=%s&models=card&limit=40" % q)
    for c in (res.get("data") or []):
        print("%-6s db=%-3s %-70s %s" % (c.get("id"), c.get("database_id"),
                                         (c.get("name") or "")[:70],
                                         (c.get("collection") or {}).get("name") or "-"))


def cmd_card(args):
    c = api("/api/card/%d" % args.id)
    print("name: %s\ndb: %s\ncollection_id: %s\ndisplay: %s" %
          (c.get("name"), c.get("database_id"), c.get("collection_id"), c.get("display")))
    print(json.dumps(c.get("dataset_query"), indent=2)[:6000])


# ---------------------------------------------------------------- guardrails

def strip_json_comments(text):
    return re.sub(r"^\s*//.*$", "", text, flags=re.M)


# Metabase's mongo editor accepts ObjectId(...) / ISODate(...), which are not valid
# JSON. We normalise them to extended JSON so the guardrails can parse the pipeline,
# then put them back before sending, so queries stay in the house style.

def normalize_mongo(text):
    text = strip_json_comments(text)
    text = re.sub(r'ObjectId\(\s*"([^"]+)"\s*\)', r'{"$oid": "\1"}', text)
    text = re.sub(r'(?:new\s+Date|ISODate)\(\s*"([^"]+)"\s*\)', r'{"$date": "\1"}', text)
    text = re.sub(r"NumberLong\(\s*\"?(-?\d+)\"?\s*\)", r"\1", text)
    text = re.sub(r",\s*([\]}])", r"\1", text)  # trailing commas
    return text


def to_mongo_text(pipeline):
    text = json.dumps(pipeline, indent=2)
    text = re.sub(r'\{\s*"\$oid":\s*"([0-9a-fA-F]{24})"\s*\}', r'ObjectId("\1")', text)
    text = re.sub(r'\{\s*"\$date":\s*"([^"]+)"\s*\}', r'ISODate("\1")', text)
    return text


def load_query(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def find_indexed(db, table):
    return set(r["path"] for r in _fields_for(db, table) if r["indexed"])


def known_paths(db, table):
    return set(r["path"] for r in _fields_for(db, table))


def match_keys(stage):
    """Field names a $match stage refers to, including inside $and / $or / $expr."""
    keys = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("$and", "$or", "$nor"):
                    if isinstance(v, list):
                        for sub in v:
                            walk(sub)
                elif k.startswith("$"):
                    walk(v)
                else:
                    keys.add(k.lstrip("$"))
                    if isinstance(v, (dict, list)):
                        walk(v)
        elif isinstance(node, list):
            for sub in node:
                walk(sub)

    walk(stage)
    return keys


def has_date_range(stage):
    text = json.dumps(stage)
    bounded = re.search(r'"\$(gte|gt|lt|lte)"', text)
    dated = re.search(r"(date|Date|createdAt|updatedAt|_at)", text)
    return bool(bounded and dated)


def check_mongo(db, table, raw, max_rows):
    """Return (errors, warnings, pipeline). Non-empty errors means blocked."""
    errors, warns = [], []
    try:
        pipeline = json.loads(normalize_mongo(raw))
    except Exception as e:
        return ([("query does not parse: %s. A mongo query must be an aggregation pipeline "
                  "array. ObjectId(...) and ISODate(...) are fine; unquoted keys and "
                  "JS expressions are not.") % e], [], None)
    if not isinstance(pipeline, list):
        return (["mongo query must be a JSON array (aggregation pipeline)"], [], None)
    if not pipeline:
        return (["pipeline is empty"], [], None)
    if not table:
        return (["--collection is required for mongo "
                 "(Metabase needs to be told the source collection)"], [], None)

    known = known_paths(db, table)
    if not known:
        errors.append("collection '%s' is not in the cached field index for db %s. Confirm the "
                      "name with: python scripts/mb.py tables %s - or run sync." % (table, db, db))
    indexed = find_indexed(db, table)
    text = json.dumps(pipeline)

    for op in MONGO_FORBIDDEN:
        if '"%s"' % op in text:
            errors.append("forbidden operator %s (it writes to the database "
                          "or runs arbitrary JS)" % op)

    first = pipeline[0]
    first_op = list(first.keys())[0] if isinstance(first, dict) and first else "?"
    if first_op != "$match":
        early = json.dumps(pipeline[:2])
        if "$limit" not in early:
            errors.append("pipeline must start with $match, or carry a $limit in the first two "
                          "stages. A bare %s reads the whole collection." % first_op)
    else:
        keys = match_keys(first)
        unknown = sorted(k for k in keys if k and k not in known and not k.startswith("$"))
        if unknown and known:
            errors.append("field(s) not in the confirmed index for %s: %s. Do not guess - check "
                          "with: python scripts/mb.py fields %s %s <pattern>"
                          % (table, ", ".join(unknown), db, table))
        if indexed and not (keys & indexed):
            errors.append("the opening $match touches no indexed field of %s. Indexed fields: %s"
                          % (table, ", ".join(sorted(indexed))[:400]))
        if table in FIREHOSE and not has_date_range(first):
            errors.append("%s is a high-volume collection: the opening $match must include a "
                          "date range ($gte / $lt on a date field)." % table)

    for st in pipeline:
        if isinstance(st, dict) and "$lookup" in st:
            lk = st["$lookup"]
            if not isinstance(lk, dict) or "pipeline" not in lk:
                errors.append("a $lookup without a sub-pipeline reads the whole joined "
                              "collection. Use let + pipeline with a $match on an indexed key, "
                              "or split it into two steps (collect ids, then $in).")

    terminal = pipeline[-1]
    agg_terminal = isinstance(terminal, dict) and any(
        k in terminal for k in ("$group", "$count", "$limit", "$sortByCount"))
    if not agg_terminal:
        warns.append('no terminal $limit: appending {"$limit": %d}' % max_rows)
        pipeline = pipeline + [{"$limit": max_rows}]
    return errors, warns, pipeline


def check_sql(db, raw, max_rows):
    errors, warns = [], []
    q = re.sub(r"--.*?$", "", raw, flags=re.M)
    q = re.sub(r"/\*.*?\*/", "", q, flags=re.S).strip().rstrip(";").strip()
    low = q.lower()
    if not (low.startswith("select") or low.startswith("with")):
        errors.append("only SELECT / WITH queries are allowed")
    m = re.search(SQL_FORBIDDEN, low)
    if m:
        errors.append("forbidden keyword '%s' - this script is read only" % m.group(1))
    if ";" in q:
        errors.append("more than one statement is not allowed")
    for t in SQL_DENY:
        if re.search(r"\b%s\b" % t, low):
            errors.append("table '%s' is off limits without an explicit human decision" % t)
    if not re.search(r"\bwhere\b", low) and not re.search(r"\blimit\b", low):
        warns.append("no WHERE clause: this reads the whole table. Saturn is Citus-distributed, "
                     "so filter on business / financial year to stay on one shard.")
    if not re.search(r"\blimit\s+\d+", low):
        warns.append("no LIMIT: wrapping the query in LIMIT %d" % max_rows)
        q = "SELECT * FROM (\n%s\n) _mb_guard LIMIT %d" % (q, max_rows)
    return errors, warns, q


def engine_for(db):
    for r in read_tsv("databases.tsv"):
        if r["id"] == str(db):
            return r["engine"]
    sys.exit("ERROR: database %s is not in the cache. Run: python scripts/mb.py sync" % db)


def build_check(args):
    raw = load_query(args.file)
    engine = engine_for(args.db)
    max_rows = args.max_rows or DEFAULT_MAX_ROWS
    if engine == "mongo":
        errors, warns, q = check_mongo(args.db, args.collection, raw, max_rows)
        return "mongo", errors, warns, q
    errors, warns, q = check_sql(args.db, raw, max_rows)
    return "sql", errors, warns, q


def report(kind, errors, warns):
    for w in warns:
        print("WARN  %s" % w)
    for e in errors:
        print("BLOCK %s" % e)
    if not errors:
        print("PASS  guardrails ok (%s)" % kind)


def cmd_check(args):
    kind, errors, warns, _ = build_check(args)
    report(kind, errors, warns)
    sys.exit(2 if errors else 0)


def native_payload(db, kind, query, collection):
    if kind == "mongo":
        native = {"query": to_mongo_text(query), "collection": collection}
    else:
        native = {"query": query}
    return {"database": int(db), "type": "native", "native": native}


def run_query(db, kind, query, collection, max_rows):
    res = api("/api/dataset", method="POST",
              body=native_payload(db, kind, query, collection), timeout=300)
    if res.get("status") == "failed" or res.get("error"):
        print("QUERY FAILED: %s" % (res.get("error") or res.get("error_type")))
        sys.exit(1)
    data = res.get("data", {})
    cols = [c.get("display_name") or c.get("name") for c in data.get("cols", [])]
    rows = data.get("rows", [])
    print("\t".join(str(c) for c in cols))
    for r in rows[:max_rows]:
        print("\t".join("" if v is None else str(v) for v in r))
    print("-- %d rows, %s ms" % (len(rows), res.get("running_time")))


def cmd_run(args):
    kind, errors, warns, query = build_check(args)
    report(kind, errors, warns)
    if errors:
        if not args.override:
            sys.exit(2)
        print("OVERRIDE accepted: %s" % args.override)
    if args.probe and kind == "mongo" and "$match" in query[0]:
        # How many documents does the filter select? That is the cost signal.
        print("-- probe: how many documents does the opening $match select? --")
        run_query(args.db, kind, [query[0], {"$count": "matched_docs"}], args.collection, 5)
        print("-- probe done, running the full query --")
    run_query(args.db, kind, query, args.collection, args.max_rows or DEFAULT_MAX_ROWS)


def cmd_save(args):
    kind, errors, warns, query = build_check(args)
    report(kind, errors, warns)
    if errors and not args.override:
        sys.exit(2)
    payload = {
        "name": args.name,
        "dataset_query": native_payload(args.db, kind, query, args.collection),
        "display": args.display,
        "visualization_settings": {},
        "collection_id": args.collection_id,
        "description": args.description,
    }
    card = api("/api/card", method="POST", body=payload)
    print("created card %s" % card.get("id"))
    print("%s/question/%s" % (base_url(), card.get("id")))


def cmd_env(args):
    url, key = load_env()
    host = re.sub(r"^https?://", "", url)
    print("metabase host: %s" % host)
    print("api key: loaded (%d chars, not shown)" % len(key))
    me = api("/api/user/current")
    print("acting as: %s (id %s, admin=%s)" % (me.get("common_name"), me.get("id"),
                                               me.get("is_superuser")))


def main():
    p = argparse.ArgumentParser(prog="mb.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("env").set_defaults(func=cmd_env)

    s = sub.add_parser("sync")
    s.add_argument("--dbs")
    s.set_defaults(func=cmd_sync)

    sub.add_parser("dbs").set_defaults(func=cmd_dbs)

    s = sub.add_parser("tables")
    s.add_argument("db")
    s.add_argument("pattern", nargs="?")
    s.set_defaults(func=cmd_tables)

    s = sub.add_parser("fields")
    s.add_argument("db")
    s.add_argument("table")
    s.add_argument("pattern", nargs="?")
    s.set_defaults(func=cmd_fields)

    s = sub.add_parser("indexes")
    s.add_argument("db")
    s.add_argument("table")
    s.set_defaults(func=cmd_indexes)

    s = sub.add_parser("cards")
    s.add_argument("search")
    s.set_defaults(func=cmd_cards)

    s = sub.add_parser("card")
    s.add_argument("id", type=int)
    s.set_defaults(func=cmd_card)

    for name in ("check", "run", "save"):
        s = sub.add_parser(name)
        s.add_argument("--db", required=True)
        s.add_argument("--file", required=True)
        s.add_argument("--collection", help="mongo source collection name")
        s.add_argument("--max-rows", type=int)
        s.add_argument("--override", help="reason for bypassing a guardrail (must be logged)")
        if name == "run":
            s.add_argument("--probe", action="store_true")
        if name == "save":
            s.add_argument("--name", required=True)
            s.add_argument("--collection-id", type=int, required=True)
            s.add_argument("--display", default="table")
            s.add_argument("--description", default="")
        s.set_defaults(func={"check": cmd_check, "run": cmd_run, "save": cmd_save}[name])

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
