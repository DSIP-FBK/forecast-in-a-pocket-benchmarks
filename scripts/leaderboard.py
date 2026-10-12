#!/usr/bin/env python3
"""Parse one benchmark issue (the issue-form body), verify it, store it and render the README leaderboard.

Inputs (env): ISSUE_NUMBER, ISSUE_BODY, ISSUE_USER, ISSUE_URL. Files: data/known_hashes.json (per family and SoC,
the sha256 of the shipped case's step-1 2t column), data/benchmarks.json (the store), README.md (the table between
the leaderboard markers). Outputs: verdict.md (the comment) and verdict.label (one of verified / unverified /
new-chip / invalid).

Verification: the phone's outputs are bit-reproducible for a given HTP generation, so a submission of the SHIPPED
case whose hash equals the known hash of its SoC was really computed by the model on that chip. A SoC we have no
hash for is "new-chip" (pending a second, independent device agreeing); a run from the latest ECMWF analysis is
"unverified" (the hash cannot be checked, the timings are still listed).
"""
import json, os, re, sys
from datetime import datetime, timezone

FIELDS = {   # issue-form label -> key
    "Device": "device", "SoC": "soc", "Android": "android", "App version": "app_version", "Model": "model",
    "Steps (6 h each)": "steps", "Seconds per step": "sps", "Total minutes": "minutes", "NPU max °C": "npu_max",
    "Initial conditions": "source", "Verification hash": "hash", "Restarts": "resumes", "Run finished at (UTC)": "run_at", "Notes": "notes",
}
START, END = "<!-- leaderboard:start -->", "<!-- leaderboard:end -->"


def parse(body: str) -> dict:
    out = {}
    for m in re.finditer(r"^### (.+?)\s*\n(.*?)(?=^### |\Z)", body.replace("\r\n", "\n"), re.S | re.M):
        label, val = m.group(1).strip(), m.group(2).strip()
        if val == "_No response_":
            val = ""
        if label in FIELDS:
            out[FIELDS[label]] = val
    return out


def num(s, cast=float):
    try:
        return cast(str(s).replace(",", ".").strip())
    except Exception:
        return None


def main():
    n = int(os.environ["ISSUE_NUMBER"]); body = os.environ.get("ISSUE_BODY", ""); user = os.environ.get("ISSUE_USER", "")
    url = os.environ.get("ISSUE_URL", "")
    f = parse(body)
    known = json.load(open("data/known_hashes.json"))
    family = "ens" if "ens" in f.get("model", "").lower() else "single"
    soc = f.get("soc", "").strip().lower()
    sps = num(f.get("sps")); steps = num(f.get("steps"), int)
    problems = []
    if not f.get("device"): problems.append("no device")
    if not soc: problems.append("no SoC")
    if sps is None or sps <= 0 or sps > 3600: problems.append("seconds per step must be a positive number")
    if steps is None or steps < 1 or steps > 400: problems.append("steps must be between 1 and 400")
    h = f.get("hash", "").strip().lower()
    shipped = f.get("source", "").lower().startswith("shipped")
    if problems:
        verdict, label = "invalid", "invalid"
        why = "; ".join(problems)
    elif not shipped:
        verdict, label = "unverified", "unverified"
        why = "a run from the latest ECMWF analysis cannot be checked against the shipped case's hash; the timings are listed as unverified"
    elif not re.fullmatch(r"[0-9a-f]{64}", h):
        verdict, label = "unverified", "unverified"
        why = "no verification hash in the form"
    elif soc not in known.get(family, {}):
        verdict, label = "new chip", "new-chip"
        why = f"no known hash yet for {soc} ({family}): pending a second, independent device with the same hash"
    elif known[family][soc] == h:
        verdict, label = "verified", "verified"
        why = f"the step-1 2t column hash matches the known {soc} hash: this is the real model on that chip"
    else:
        verdict, label = "hash mismatch", "unverified"
        why = f"the hash differs from the known {soc} hash (a different cell set, a corrupted run, or a hand-edited form)"

    entry = {
        "issue": n, "user": user, "url": url, "device": f.get("device", ""), "soc": soc, "android": f.get("android", ""),
        "app_version": f.get("app_version", ""), "family": family, "steps": steps, "sps": sps, "minutes": num(f.get("minutes")),
        "npu_max": num(f.get("npu_max"), int), "source": f.get("source", ""), "hash": h, "resumes": num(f.get("resumes"), int) or 0,
        "run_at": f.get("run_at", ""), "verdict": verdict, "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    }
    store = json.load(open("data/benchmarks.json")) if os.path.exists("data/benchmarks.json") else []
    store = [e for e in store if e.get("issue") != n]
    if verdict != "invalid":
        store.append(entry)
    store.sort(key=lambda e: (e["family"], e["sps"] if e.get("sps") else 1e9))
    json.dump(store, open("data/benchmarks.json", "w"), indent=1)

    # the README table(s): one per family, fastest first
    mark = {"verified": "✓ verified", "new chip": "new chip", "unverified": "unverified", "hash mismatch": "✗ mismatch"}
    lines = [START, ""]
    for fam, title in (("single", "AIFS-single"), ("ens", "AIFS-ENS (one member)")):
        rows = [e for e in store if e["family"] == fam]
        lines += [f"### {title}", ""]
        if not rows:
            lines += ["_no submissions yet_", ""]
            continue
        lines += ["| # | device | SoC | s/step | steps | total min | NPU max | initial conditions | app | status | by |",
                  "|--:|---|---|--:|--:|--:|--:|---|---|---|---|"]
        for i, e in enumerate(rows, 1):
            lines.append("| {} | {} | {} | {:.1f} | {} | {} | {} | {} | {} | {} | [@{}]({}) |".format(
                i, e["device"], e["soc"], e["sps"], e["steps"], "" if e["minutes"] is None else f"{e['minutes']:.0f}",
                "" if e["npu_max"] is None else f"{e['npu_max']} °C", e["source"] or "", e["app_version"], mark.get(e["verdict"], e["verdict"]),
                e["user"], e["url"]))
        lines.append("")
    lines.append(END)
    readme = open("README.md").read()
    a, b = readme.find(START), readme.find(END)
    if a >= 0 and b >= 0:
        readme = readme[:a] + "\n".join(lines) + readme[b + len(END):]
        open("README.md", "w").write(readme)

    open("verdict.label", "w").write(label)
    open("verdict.md", "w").write(
        f"**{verdict}** - {why}.\n\n" +
        ("" if verdict == "invalid" else f"Listed in the [leaderboard](https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}#leaderboard): "
         f"{entry['device']} ({soc}), AIFS-{family}, {sps} s/step over {steps} steps.\n") +
        "\n_This comment was written by the leaderboard Action; edit the issue to correct a field and it runs again._\n")
    print(json.dumps(entry, indent=1))


if __name__ == "__main__":
    sys.exit(main())
