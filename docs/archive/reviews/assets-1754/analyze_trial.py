"""Analyze trial-8 Scenes produced by run_batch.py; inputs are read-only."""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT: Path | None = None
DESIGNS = ("executive-light", "target-b", "marquee")
OBJ_ROW = re.compile(r'review-lane:\[.*?"([^"]+)"\]')


def load_week(w: int):
    proj = json.loads((ROOT / f"w{w}" / "project.yaml").read_text())
    sch = json.loads((ROOT / f"w{w}" / "schedule.json").read_text())["placements"]
    act = json.loads((ROOT / f"w{w}" / "actual.yaml").read_text())["body"]
    latest = {}
    for observation in act["observations"]:
        oid = observation["projectObjectId"]
        if oid not in latest or observation["sequence"] > latest[oid]["sequence"]:
            latest[oid] = observation
    return proj, sch, act["asOf"], latest


def object_signatures(w: int):
    proj, schedule, asof, latest = load_week(w)
    rels = {r["id"]: r for r in proj["relations"]}
    incidence = collections.defaultdict(set)
    for rid, relation in rels.items():
        incidence[relation["from"]["object"]].add(rid)
        incidence[relation["to"]["object"]].add(rid)
    full, task_semantics = {}, {}
    for oid, obj in proj["objects"].items():
        observation = latest.get(oid)
        actual = dict(observation["actual"]) if observation else None
        if actual and actual.get("openUntil") == "asOf":
            actual["openUntil"] = asof
        core = [obj.get("title"), obj.get("fields"), obj.get("deadline"),
                schedule.get(oid), actual]
        full[oid] = json.dumps([*core, sorted(incidence[oid])], sort_keys=True)
        if obj.get("type") == "work":
            # Task identity comparison intentionally excludes relation incidence.
            task_semantics[oid] = json.dumps(core, sort_keys=True)
    relation_signatures = {rid: json.dumps(r, sort_keys=True) for rid, r in rels.items()}
    return full, relation_signatures, rels, task_semantics


def owner(p, rels):
    sr = p.get("sourceRef", "")
    # New canonical identity: relation:id:<percent-encoded declared relation ID>.
    if sr.startswith("relation:id:"):
        candidate = unquote(sr[len("relation:id:"):])
        if candidate in rels:
            return "rel", candidate
        # Some producer references include the identity as one opaque token.
        if sr in rels:
            return "rel", sr
    # Legacy indexed source references remain understood for old Scene evidence.
    m = re.match(r"relation:\d+:(.+)$", sr)
    if m:
        return "rel", m.group(1)
    m = OBJ_ROW.match(sr)
    if m:
        return "obj", m.group(1)
    if p.get("laneMemberId"):
        return "obj", p["laneMemberId"]
    return ("obj", sr) if sr else ("global", p["id"])


def norm_id(ident):
    # Preserve canonical relation:id identities; normalize only legacy indices.
    return re.sub(r"^relation:(\d+):", "relation:", ident)


def row_index(scene):
    rows = []
    for row in scene["surfaces"][0]["rows"]:
        m = OBJ_ROW.match(row["id"])
        rows.append((row["bounds"]["block"], row["bounds"]["blockSize"],
                     m.group(1) if m else row["id"]))
    return sorted(rows)


def ny(y, rows):
    prev = None
    for block, size, oid in rows:
        if y < block - 0.01:
            break
        prev = block, size, oid
    if prev is None:
        return "abs", round(y, 1)
    block, _, oid = prev
    return oid, round(y - block, 1)


def mappts(x, f):
    if isinstance(x, dict):
        return {k: mappts(v, f) for k, v in x.items()}
    if isinstance(x, list):
        if len(x) == 2 and all(isinstance(v, (int, float)) for v in x):
            return [x[0], f(x[1])]
        return [mappts(v, f) for v in x]
    return x


def geom(p, rows=None):
    f = (lambda y: round(y, 1)) if rows is None else (lambda y: ny(y, rows))
    result = {"kind": p["kind"], "text": p.get("text"),
              "paint": json.dumps(p.get("paint"), sort_keys=True),
              "symbol": mappts(p.get("symbol"), f)}
    bounds = p.get("bounds")
    if bounds:
        result["b"] = (round(bounds["inline"], 1), f(bounds["block"]),
                        round(bounds["inlineSize"], 1), round(bounds["blockSize"], 1))
    if p.get("points"):
        result["pts"] = [(round(x, 1), f(y)) for x, y in p["points"]]
    return result


def flatten(value):
    if isinstance(value, dict):
        out = []
        for key in sorted(value):
            out.extend((key, *flatten(value[key])))
        return out
    if isinstance(value, (list, tuple)):
        out = ["["]
        for item in value:
            out.extend(flatten(item))
        return out + ["]"]
    return [value]


def same(a, b, tol=0.5):
    fa, fb = flatten(a), flatten(b)
    if len(fa) != len(fb):
        return False
    for x, y in zip(fa, fb):
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
            if abs(x - y) > tol:
                return False
        elif x != y:
            return False
    return True


def warn_counts(receipt, design, week, variant):
    rec = next((r for r in receipt if r.get("design") == design and r.get("week") == week
                and r.get("variant") == variant), None)
    if not rec:
        return collections.Counter(), {"seconds": None, "warnings": []}
    payload = rec.get("stdoutJson") or {}
    counts = collections.Counter()
    for warning in payload.get("warnings", []):
        counts[warning["code"]] += warning.get("count", 1)
    return counts, {"seconds": rec.get("elapsedSeconds"), "warnings": payload.get("warnings", []),
                    "diagnostics": payload.get("diagnostics", []),
                    "processOutcome": rec.get("processOutcome"),
                    "returnCode": rec.get("returnCode")}


def text_overlaps(scene):
    texts = [p for p in scene["surfaces"][0]["primitives"] if p["kind"] == "Text" and p.get("bounds")]
    count, examples = 0, []
    for i, a in enumerate(texts):
        ab = a["bounds"]
        for b in texts[i + 1:]:
            bb = b["bounds"]
            ox = min(ab["inline"] + ab["inlineSize"], bb["inline"] + bb["inlineSize"]) - max(ab["inline"], bb["inline"])
            oy = min(ab["block"] + ab["blockSize"], bb["block"] + bb["blockSize"]) - max(ab["block"], bb["block"])
            if ox > 1 and oy > 1:
                count += 1
                examples.append((a.get("text"), b.get("text")))
    viewport = scene["viewport"]
    clipped = [p.get("text") for p in texts if p["bounds"]["inline"] < -0.5
               or p["bounds"]["inline"] + p["bounds"]["inlineSize"] > viewport["inlineSize"] + 0.5
               or p["bounds"]["block"] + p["bounds"]["blockSize"] > viewport["blockSize"] + 0.5]
    return count, examples[:6], clipped[:6]


def label_side(scene):
    primitives = scene["surfaces"][0]["primitives"]
    bars = {p["sourceRef"]: p["bounds"] for p in primitives
            if p.get("purpose") == "planned" and p.get("bounds")}
    sides = {}
    for p in primitives:
        if p.get("purpose") != "member-label":
            continue
        bar = bars.get(p.get("sourceRef"))
        if not bar or not p.get("bounds"):
            continue
        label = p["bounds"]
        if label["inline"] >= bar["inline"] + bar["inlineSize"] - 2:
            side = "end"
        elif label["inline"] + label["inlineSize"] <= bar["inline"] + 2:
            side = "start"
        else:
            side = "inside"
        sides[p["sourceRef"]] = side
    return sides


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True, type=Path,
                        help="Pinned trial-8 directory from bf3940dbe9af487ac6cace5458554762594f3477")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--variant", choices=("plain", "hint"), default="plain")
    args = parser.parse_args()
    global ROOT
    ROOT = args.input_root.expanduser().resolve()
    if not (ROOT / "w1" / "project.yaml").is_file():
        parser.error(f"trial input directory not found: {ROOT}")
    out = args.output_dir.resolve() / args.variant
    receipt_data = json.loads((args.output_dir.resolve() / "receipt.json").read_text())
    records = receipt_data["records"]
    sigs = {week: object_signatures(week) for week in range(1, 6)}
    detail, pair_rows = {}, []
    for design in DESIGNS:
        scenes = {}
        for week in range(1, 6):
            path = out / f"{design}-w{week}.scene.json"
            if args.variant == "hint" and week == 1 and not path.is_file():
                # The batch runner deliberately reuses the plain W1 artifact.
                path = args.output_dir.resolve() / "plain" / f"{design}-w1.scene.json"
            if path.is_file():
                scenes[week] = json.loads(path.read_text())
        for week, scene in scenes.items():
            overlap_count, overlap_examples, clipped = text_overlaps(scene)
            rec_variant = "plain" if args.variant == "hint" and week == 1 else args.variant
            warning_counts, rec = warn_counts(records, design, week, rec_variant)
            legend = [p.get("text") for p in scene["surfaces"][0]["primitives"]
                      if p.get("purpose") == "legend-label"]
            detail[f"{design}-w{week}"] = {
                "canvas": scene["viewport"], "textOverlaps": overlap_count,
                "overlapExamples": overlap_examples, "clippedText": clipped,
                "legend": legend, "warnings": dict(warning_counts),
                "seconds": rec["seconds"], "processOutcome": rec["processOutcome"],
                "returnCode": rec["returnCode"], "diagnostics": rec["diagnostics"],
                "domain": [scene["surfaces"][0]["scale"]["domainStart"],
                           scene["surfaces"][0]["scale"]["domainEnd"]]}
        for week in range(2, 6):
            if week not in scenes or week - 1 not in scenes:
                continue
            before, after = scenes[week - 1], scenes[week]
            (sig_a, rel_a, rels_a, tasks_a), (sig_b, rel_b, rels_b, tasks_b) = sigs[week - 1], sigs[week]
            unchanged_obj = {oid for oid in sig_a if oid in sig_b and sig_a[oid] == sig_b[oid]}
            unchanged_rel = {rid for rid in rel_a if rid in rel_b and rel_a[rid] == rel_b[rid]
                             and rels_a[rid]["from"]["object"] in unchanged_obj
                             and rels_a[rid]["to"]["object"] in unchanged_obj}
            unchanged_tasks = {oid for oid in tasks_a if oid in tasks_b and tasks_a[oid] == tasks_b[oid]}
            rows_a, rows_b = row_index(before), row_index(after)
            pa = {norm_id(p["id"]): p for p in before["surfaces"][0]["primitives"]}
            pb = {norm_id(p["id"]): p for p in after["surfaces"][0]["primitives"]}
            raw_a = {p["id"] for p in before["surfaces"][0]["primitives"]}
            raw_b = {p["id"] for p in after["surfaces"][0]["primitives"]}
            counts, examples, total_unchanged = collections.Counter(), collections.defaultdict(list), 0
            for key, primitive in pa.items():
                kind, oid = owner(primitive, rels_a)
                if not ((kind == "obj" and oid in unchanged_obj) or (kind == "rel" and oid in unchanged_rel)):
                    continue
                total_unchanged += 1
                other = pb.get(key)
                if other is None:
                    counts["removed"] += 1
                    examples["removed"].append(key[:90])
                    continue
                if primitive["id"] not in raw_b:
                    counts["id-renumbered"] += 1
                if not same(geom(primitive), geom(other)):
                    counts["raw"] += 1
                    if not same(geom(primitive, rows_a), geom(other, rows_b)):
                        counts["row-normalised"] += 1
                        category = kind if kind == "rel" else primitive.get("purpose")
                        counts[f"rn:{category}"] += 1
                        examples[f"rn:{category}"].append(oid)
            for key, primitive in pb.items():
                kind, oid = owner(primitive, rels_b)
                if ((kind == "obj" and oid in unchanged_obj) or (kind == "rel" and oid in unchanged_rel)) and key not in pa:
                    counts["added"] += 1
                    examples["added"].append(key[:90])
            sides_a, sides_b = label_side(before), label_side(after)
            flips = [oid for oid in sides_a if oid in sides_b and oid in unchanged_obj and sides_a[oid] != sides_b[oid]]
            task_labels_a = {p.get("laneMemberId") for p in before["surfaces"][0]["primitives"]
                             if p.get("purpose") == "member-label" and p.get("laneMemberId")}
            task_labels_b = {p.get("laneMemberId") for p in after["surfaces"][0]["primitives"]
                             if p.get("purpose") == "member-label" and p.get("laneMemberId")}
            task_gone = sorted((task_labels_a - task_labels_b) & unchanged_tasks)
            task_new = sorted((task_labels_b - task_labels_a) & unchanged_tasks)
            variant_a = "plain" if args.variant == "hint" and week - 1 == 1 else args.variant
            variant_b = "plain" if args.variant == "hint" and week == 1 else args.variant
            wa, _ = warn_counts(records, design, week - 1, variant_a)
            wb, _ = warn_counts(records, design, week, variant_b)
            warning_delta = {code: wb.get(code, 0) - wa.get(code, 0)
                             for code in set(wa) | set(wb) if wb.get(code, 0) != wa.get(code, 0)}
            pair_rows.append({"design": design, "pair": f"w{week-1}->w{week}",
                              "unchangedObjects": len(unchanged_obj), "unchangedRelations": len(unchanged_rel),
                              "primsOfUnchanged": total_unchanged, **dict(counts),
                              "labelSideFlips": flips, "unchangedTaskLabelGone": task_gone,
                              "unchangedTaskLabelNew": task_new,
                              "unchangedTaskLabelToggleCount": len(task_gone) + len(task_new),
                              "canvas": (before["viewport"]["blockSize"], after["viewport"]["blockSize"]),
                              "warnDelta": warning_delta,
                              "examples": {k: sorted(set(v))[:12] for k, v in examples.items()}})
    result = {"variant": args.variant, "pairs": pair_rows, "weeks": detail}
    (out / "analysis-batch.json").write_text(json.dumps(result, indent=1, default=str) + "\n")
    for row in pair_rows:
        print(row["design"], row["pair"], {k: v for k, v in row.items()
              if k not in ("design", "pair", "examples")})
    for key, value in detail.items():
        print(key, value["canvas"], "overlaps", value["textOverlaps"],
              value["overlapExamples"][:3], "clipped", value["clippedText"],
              "legend", value["legend"], value["seconds"], value["domain"])


if __name__ == "__main__":
    main()
