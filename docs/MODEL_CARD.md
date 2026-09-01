# Model card — `vernier-instrument`

A small open model that reproduces `gemini-2.5-flash`'s hand-visibility and
active-manipulation judgements on egocentric frames, so a quality measurement can be re-run
on any corpus by anyone, rather than existing as one number published once.

Card shape is fixed now; values marked *produced by* name the experiment that fills them.
Nothing is trained yet.

## What it is for

Turning a single-shot vendor statistic into a **re-runnable instrument with a stated floor**.
Following Trust-or-Escalate (2407.18370), it abstains rather than always answering: what it
reports is an agreement floor against human gold and the coverage at which that floor holds. A buyer measures
the batch they are actually purchasing; a researcher measures a corpus vernier never touched;
a third party reproduces the whole audit with no API keys.

## What it deliberately is not

**It is not a better hand detector.** Training targets are the judge's labels, not human
gold, so the model reproduces the judge *including its errors*. An instrument that quietly
improved on the thing it measures would no longer measure it. `DECISIONS.md` D007.

Anyone wanting an accurate hand-state model should train on human gold and call it something
else.

## Architecture and training

| | |
|---|---|
| Rung 1 | Linear probe on frozen features. Backbone fixed by `SURVEY.md`. Laptop-runnable; the baseline that must be beaten to justify rung 2. |
| Rung 2 | Qwen3-VL, 4-bit LoRA, Modal L4 24 GB. Recipe inherited from `suture`. |
| Rung 3 | Confidence estimation + abstention cascade, escalating low-confidence frames. The guarantee, not the model, is the product. |
| Targets | `gemini-2.5-flash`, prompt P0, over `S10k-S` |
| Held out | Human gold `G200-ego` — never trained on, for either rung |
| Seed | 777 |

## Evaluation

Three numbers, all *produced by* E7 and E8:

1. **Agreement with the teacher** (κ, per class, against a constant-answer baseline — raw
   agreement alone is uninformative at a 96% base rate; `RED-TEAM.md` A8).
2. **Agreement with human gold**, the same statistic the teacher is scored on, so teacher and
   distillate are directly comparable.
3. **Error inheritance**: does the distillate make the teacher's mistakes, or different ones?
   This is the number that decides whether it is an instrument or merely a cheaper model.

4. **Coverage at a given floor** — the headline. H6 pre-registers ≥ 0.80 agreement at ≥ 0.70
   coverage on the hand task. Teacher fidelity (≥ 0.90 on hand presence) is the diagnostic.

## Limitations, known before training

Inherits every bias of its teacher by construction. Validated against one rater. Trained on
factory-domain frames; behaviour on other domains is the subject of E6 and is not assumed.
Per-frame only — no temporal or clip-level judgement.

## License

Apache-2.0.
