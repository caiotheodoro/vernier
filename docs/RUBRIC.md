# Annotation rubric

Revision `1.2.0`. Frozen with `PRE-REGISTRATION.md`; the revision is recorded on every
`HumanLabel`.

Revised from `1.0.0` after reading Build AI's shipped prompts directly rather than the press
paraphrase of them (`UPSTREAM-FINDINGS.md` F1, F3). Their prompts are structured and carry
five explicit rules each. **Four of the nine ambiguities `1.0.0` claimed to resolve were
already resolved upstream**, and this revision follows their rules instead of restating them
as vernier's own. That correction is recorded rather than quietly absorbed; it is the same
discipline this project applies to the thing it audits.

Revised again to `1.2.0` after an offline rubric-pilot self-check (`docs/DECISIONS.md` D036)
found `dark` in the closed tag list with no rule ever instructing a rater to apply it — Rule 9
mentioned darkness only as one cause of `undecidable`, never as its own distinct case. Rule 9
below is new; the former Rule 9 (`undecidable`) is renumbered Rule 10.

**What remains is still a finding.** Five questions are genuinely undefined by their prompts,
and each is a place where the published number could move without the data changing at all.
The largest is gloves, in a corpus of factory work.

The rubric deliberately follows Build AI's intent rather than improving on it. vernier
measures their judge; a rubric that scored a different construct would measure nothing.

Upstream prompt text is pinned verbatim in `docs/upstream/`.

## Task 1 — hand count

> P0: *"count how many camera-wearer's hands are visibly present in the image"*

Answer ∈ {0, 1, 2}.

**Rules.**

1. **Camera-wearer only.** Another person's hands are never counted. Where wearer and
   non-wearer cannot be distinguished, see Rule 9.
2. **Any part counts.** A hand is visible if any part of it — finger, knuckle, thumb, palm,
   back — is visible. Build AI's wording is "visibly present", not "fully visible", and the
   published 96.42% is implausible under a strict reading. Tagged `partial`.
3. **Gloves count.** A gloved hand is a hand. The corpus is factory work and gloves are
   near-universal; excluding them would make the metric meaningless. **P0 does not say
   this**, which is why P3 exists. Tagged `glove`.
4. **Sleeves and cuffs do not.** A covered forearm with no hand visible is 0 for that hand.
5. **Occlusion by a held object counts as visible only if hand pixels remain.** A hand fully
   behind the workpiece is not visible, even when its presence is obvious from context.
   Tagged `tool-occlusion`.
6. **Reflections and screens do not count.** A hand seen only in a mirror, monitor or
   polished surface is not present in frame. Tagged `reflection`.
7. **Motion blur counts if identifiable.** A blurred hand is a hand where it can still be
   identified as one. Where it cannot, Rule 9. Tagged `blur`.
8. **Frame edge.** A hand partly outside the frame counts if the in-frame part is
   identifiable as a hand. Tagged `edge`.
9. **Low light.** Tag `dark` when illumination is poor but a judgement is still reachable
   under the rules above; set `difficulty` to at least `medium`. Escalate to Rule 10 only when
   darkness makes no judgement reachable at all — `dark` and `undecidable` are never the same
   frame's tag for the same reason.
10. **Undecidable.** If a rule cannot be applied — ambiguous ownership, unidentifiable blur,
    darkness too severe to judge even under Rule 9 — record the best judgement, tag
    `undecidable`, and set `difficulty: hard`. The `undecidable` rate is published; it is the
    honest measure of how much of the metric is guesswork, and Build AI's judge has no
    equivalent.

## Task 2 — active manipulation

Answer ∈ {true, false}.

**Which criterion?** The dataset card and the shipped prompt file give different definitions
(`UPSTREAM-FINDINGS.md` F2). The rater labels against the **shipped file**, `P0b`, because it
is the artifact with a pinned revision — and the divergence is itself measured, as H1b.

### Upstream rules, followed as written

1. **Do not infer actions that are not visible in the frame.**
2. **If the action is ambiguous or not clearly happening, answer `false`.** Their prompt says
   respond "no". This is an explicit tie-break and the rater uses it rather than guessing.
3. **Ignore actions performed by other people** (`P0b`). Note the card says "ignore objects
   held by other people", a different exclusion; frames where this distinction bites are
   tagged `other-person` so the divergence can be quantified.

### What their prompt does not decide

4. **Contact is required.** Reaching toward an object without contact is `false`. Their
   definition is silent; P5 and P6 bracket it deliberately.
5. **Handling counts even without modification.** "Handle" is in the criterion: carrying,
   holding, moving and placing are all `true`.
6. **Tool use counts.** Acting on an object through a held tool is `true`.
7. **Operating a machine counts** when hands contact controls, workpiece or material.
8. **Idle grip is `false`.** Holding a tool while doing nothing with it, or resting a hand on
   a bench, is not manipulation. Tagged `idle-grip`. This is the single largest source of
   expected disagreement between rater and judge, and the reason H3 predicts wider spread on
   this task. Their "in pursuit of a specific goal" clause cannot be evaluated from a single
   frame at all, which is why the rater falls back to upstream Rule 2.
9. **Gesturing, pointing, and communication are `false`.** Tagged `gesture`.
10. **Self-contact is `false`.** Adjusting gloves, wiping a face, touching one's own clothing.
   Tagged `self-contact`.
11. **Ambiguous instants within an action are labelled by the frame, not the inferred
   activity.** A frame captured mid-release, between two manipulations, is `false` if no
   contact is visible at that instant. Frames are the unit of the published metric, so they
   must be the unit of the rubric. Tagged `between-actions`.
12. **Zero hands visible implies `false`.** No hands, no hand manipulation.

## Tag list, closed

`partial`, `glove`, `tool-occlusion`, `reflection`, `blur`, `edge`, `undecidable`,
`idle-grip`, `gesture`, `self-contact`, `between-actions`, `dark`, `other-person`.

A frame needing a tag outside this list means the rubric is incomplete. That is recorded in
`DECISIONS.md` and the rubric revision increments — it is never silently extended, because a
rubric that grows during labelling is a rubric fitted to the data.

## Procedure

- Frames are presented in random order, blind to corpus wherever the image does not give it
  away, and **the labelling tool never displays any judge output**.
- Both tasks are answered per frame, in one pass.
- Difficulty is recorded at label time, not afterwards.
- No frame is revisited within a pass. Revision is the `retest` pass, which is blind and runs
  at least seven days later on `R100`.
- Time per frame is recorded. It is the honest input to any cost claim about human labelling
  versus a judge.

## The limits of this rubric

- **One rater.** No inter-rater agreement exists. The `R100` re-label gives intra-rater
  agreement instead, which measures consistency and not correctness. `RED-TEAM.md` is
  explicit about the difference.
- **The rater read both prompts first.** These rules were written knowing the wording being
  audited — and `1.1.0` was revised *after* reading them. That anchoring cannot be removed at
  n = 1, only declared. `RED-TEAM.md` A2.
- **The rubric is an interpretation.** Five ambiguities were resolved by judgement, four
  having turned out to be already settled upstream. A
  different reasonable reading gives different numbers — which is precisely the claim vernier
  is making about the published metric, and it applies here with equal force.
