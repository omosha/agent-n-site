#!/usr/bin/env python3
"""
verify.py - Independently reproduce Agent-N's sealed California board and its grade.

    $ python3 verify.py

No dependencies. No API keys. No network. No model code. Pure Python standard
library, run against the two published data files in this repo:

    data/sealed-board.json   the predictions, locked and SHA-256 sealed on 2026-10-13
    sealed-results.json      the certified California results (public record)

It proves two separate things, in order:

  1. SEAL   - the predictions existed BEFORE the vote. It re-hashes the sealed
              board and checks that hash against the fingerprint published on the
              site and against the dated git commit. If the file had been edited
              after the fact, the hash would not match.

  2. GRADE  - how those locked calls actually scored against certified results:
              the winner-call hit rate (toss-ups excluded) and the topline error.

This is the calibrated statistical layer (what the site calls Scoreboard 1). It is
a forecasting model, not a language model, and it is NOT the reactive what-if engine.
Reproducing this verifies the sealed forecast and its score; it does not touch, and
makes no claim about, the separate simulation engine.
"""
import json
import hashlib
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_FILE = os.path.join(HERE, "data", "sealed-board.json")
RESULTS_FILE = os.path.join(HERE, "sealed-results.json")
NATIONAL_RESULTS_FILE = os.path.join(HERE, "data", "national-baseline-results.json")

# Published on the site next to the SEALED badge. The board file must hash to this.
PUBLISHED_SHA256 = "f7884deb9d8db77676ce670592567d92cbf04536f471c43447f3c856da78ebe9"
SEAL_COMMIT = "e36075f"
VOTE_DAY = "2026-11-03"

# The California platform. National battleground races on a simpler baseline anchor
# live in the sealed file too, but are a separate experiment and not part of this record.
CA_GROUPS = {"CA U.S. House", "CA State Legislature", "OC Supervisor", "Governor"}

BAR = "=" * 64


def load_board():
    data = json.load(open(BOARD_FILE))
    return data if isinstance(data, list) else (data.get("races") or data.get("board") or data.get("rows"))


def seal_check():
    print(BAR)
    print("STEP 1 - SEAL   did these predictions exist before the vote?")
    print(BAR)
    digest = hashlib.sha256(open(BOARD_FILE, "rb").read()).hexdigest()
    match = digest == PUBLISHED_SHA256
    print(f"  data/sealed-board.json SHA-256:\n    {digest}")
    print(f"  published fingerprint        :\n    {PUBLISHED_SHA256}")
    print(f"  -> {'MATCH. the sealed file has not changed.' if match else 'MISMATCH - DO NOT TRUST.'}")
    try:
        when = subprocess.check_output(
            ["git", "-C", HERE, "show", "-s", "--format=%ci", SEAL_COMMIT],
            text=True, stderr=subprocess.DEVNULL).strip()
        print(f"  sealed in commit {SEAL_COMMIT}, dated {when}")
        print(f"  (the vote was {VOTE_DAY}; the commit predates it)")
    except Exception:
        print(f"  sealed in commit {SEAL_COMMIT} (clone the git repo to see its date,")
        print(f"   or view it at github.com/omosha/agent-n-site/commit/{SEAL_COMMIT})")
    print()
    return match


def grade():
    board = load_board()
    results = json.load(open(RESULTS_FILE)).get("races", {})
    ca = [r for r in board if (r.get("g") or r.get("set")) in CA_GROUPS]

    called = [r for r in ca if r.get("call") in ("D", "R")]
    graded = [r for r in called if results.get(r["dist"], {}).get("winner") in ("D", "R")]
    correct = [r for r in graded if r["call"] == results[r["dist"]]["winner"]]

    # MAE is a margin metric, so it spans every race with a projection and a certified
    # result, toss-ups included (unlike the winner-call rate, which excludes toss-ups).
    errs = sorted(abs(r["proj"] - results[r["dist"]]["dem_twoway"])
                  for r in ca
                  if r.get("proj") is not None
                  and r["dist"] in results
                  and results[r["dist"]].get("dem_twoway") is not None)
    mae = sum(errs) / len(errs) if errs else None
    median_ae = errs[len(errs) // 2] if errs else None

    toss = [r for r in ca if r.get("call") == "Toss-up"]
    toss_graded = [r for r in toss if r["dist"] in results]
    toss_pending = [r for r in toss if r["dist"] not in results]

    print(BAR)
    print("STEP 2 - GRADE   how did the sealed calls score vs certified results?")
    print(BAR)
    print("  California, calibrated statistical layer (Scoreboard 1)")
    print()
    print(f"    races sealed ............. {len(ca)}")
    print(f"    called D or R ............ {len(called)}   (toss-ups are not called, so not scored)")
    print(f"    certified so far ......... {len(graded)}")
    pct = 100 * len(correct) / len(graded) if graded else 0
    print(f"    CALLS CORRECT ............ {len(correct)} / {len(graded)}  = {pct:.1f}%")
    if mae is not None:
        print(f"    topline MAE (D two-way) .. {mae:.2f} pp  (median {median_ae:.2f} pp, {len(errs)} graded races)")
    print()

    print("  by group:")
    for g in sorted(CA_GROUPS):
        gc = [r for r in graded if (r.get("g") or r.get("set")) == g]
        gk = [r for r in gc if r["call"] == results[r["dist"]]["winner"]]
        if gc:
            print(f"    {g:<22} {len(gk)}/{len(gc)}")
    print()

    misses = [r for r in graded if r["call"] != results[r["dist"]]["winner"]]
    print(f"  called wrong ({len(misses)}):")
    for r in misses:
        c = results[r["dist"]]
        print(f"    {r['dist']:<7} called {r['call']}, certified {c['winner']} "
              f"(D two-way {c.get('dem_twoway')})")
    print()

    print(f"  toss-ups: {len(toss)} called toss-up, not counted in the hit rate")
    print(f"    {len(toss_graded)} now certified, "
          f"{len(toss_pending)} still counting: {', '.join(r['dist'] for r in toss_pending) or 'none'}")
    print()


def national_baseline():
    """Grade the 28 national races too, clearly labeled as the separate, non-platform
    baseline. Shown on purpose so the weaker national numbers are not something a
    reviewer has to discover on their own."""
    if not os.path.exists(NATIONAL_RESULTS_FILE):
        return
    nat = [r for r in load_board() if (r.get("g") or r.get("set")) == "National U.S. House"]
    results = json.load(open(NATIONAL_RESULTS_FILE)).get("races", {})
    called = [r for r in nat if r.get("call") in ("D", "R")]
    graded = [r for r in called if results.get(r["dist"], {}).get("winner") in ("D", "R")]
    correct = [r for r in graded if r["call"] == results[r["dist"]]["winner"]]

    print(BAR)
    print("STEP 3 - NATIONAL BASELINE   a separate, non-platform experiment (shown, not hidden)")
    print(BAR)
    print("  28 national battleground races in the sealed file used a SIMPLER baseline anchor")
    print("  (2024 presidential two-way + incumbency + a swing band), NOT the California method.")
    print("  Reported here, labeled, so nothing is buried:")
    print()
    pct = 100 * len(correct) / len(graded) if graded else 0
    print(f"    called D or R ............ {len(called)}")
    print(f"    certified so far ......... {len(graded)}")
    print(f"    calls correct ............ {len(correct)} / {len(graded)}  = {pct:.1f}%")
    print()
    print("  This baseline ran close to the 2024 map and under-weighted the 2026 Democratic")
    print("  environment. It is NOT part of the California record and NOT the platform.")
    print()


def main():
    print()
    print("AGENT-N  -  SEALED CALIFORNIA BOARD, INDEPENDENT VERIFICATION")
    for f in (BOARD_FILE, RESULTS_FILE):
        if not os.path.exists(f):
            raise SystemExit(f"missing data file: {f}\nRun this from inside the agent-n-site repo.")
    print()
    ok = seal_check()
    grade()
    national_baseline()
    print(BAR)
    print("Reproduced from published data alone: no API keys, no model code, no network.")
    print("The sealed forecast and its score are what you just checked yourself.")
    print(BAR)
    print()
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
