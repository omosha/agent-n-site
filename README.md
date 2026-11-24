# Agent-N sealed California board

The predictions on [agent-n-site.vercel.app](https://agent-n-site.vercel.app) are
pre-registered: locked and SHA-256 sealed **before** the 2026-11-03 vote, then graded
in public against certified results. You do not have to take any of that on faith.

## Reproduce it yourself, one command

No dependencies, no API keys, no network, no model code. Just Python 3:

```sh
python3 verify.py
```

It does two things, in order:

1. **Seal.** Re-hashes `data/sealed-board.json` and checks the hash against the
   fingerprint published on the site and against the dated git commit
   (`e36075f`, 2026-10-13, which predates the vote). If the file had been edited
   after the results came in, the hash would not match.
2. **Grade.** Scores those locked calls against `sealed-results.json` (the certified
   California results) and prints the winner-call hit rate and the topline error.

Expected output: the seal matches, and the board called **104 / 109 = 95.4%**
(toss-ups excluded), topline **MAE 6.01pp**, with the 5 misses and 14 toss-ups
itemized so nothing is hidden.

## What this does and does not prove

- It verifies the **calibrated statistical layer** (the forecasting model) and its
  score. This is a forecasting model, not a language model.
- It is **not** the reactive what-if simulation engine, and it makes no claim about it.
  That engine is a separate capability, evaluated separately, and is not in this repo.

## The two data files

| File | What it is |
| --- | --- |
| `data/sealed-board.json` | The sealed predictions. Do not edit it; the hash is the proof. |
| `sealed-results.json` | Certified California results, the public record the board is graded against. |

The 28 national battleground races in the sealed file used a simpler baseline anchor;
they are a separate experiment, not part of the California record. `verify.py` grades
them too (STEP 3), clearly labeled, so the weaker national numbers are shown rather than
buried: that baseline ran close to the 2024 map and under-weighted the 2026 Democratic
environment.
