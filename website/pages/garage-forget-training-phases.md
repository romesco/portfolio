---
title: "Forget about Pre-training, Mid-Training, and Post-Training"
description: "Drafting in the open: rethinking the pre-training / mid-training / post-training taxonomy as one continuous process."
authors:
  - Rosario Scalise
---

> **Stub.** This one is an outline in the open: the argument is still being
> drafted. Check back, or read [Compression via Continuous Optimization is
> Intelligence](/garage-compression-is-intelligence) in the meantime.

**Working thesis.** <!-- AI-DRAFT --> The split between *pre-training*,
*mid-training*, and *post-training* is an artifact of tooling and org charts,
not a fact about learning. It is all one continuous optimization against a
moving data distribution: the boundaries are where a checkpoint got handed from
one team (or one budget) to the next, and treating them as distinct *kinds* of
learning obscures more than it explains.

## Outline

- What the three-phase story claims, and why it is convenient.
- Where the boundaries actually come from (data, compute budgets, ownership),
  not from anything intrinsic to the optimization.
- The continuous-optimization view: one objective, one trajectory, curriculum
  as a schedule rather than a phase change.
- What this reframing buys us, and what it costs.

## Notes to self

- Connect to the compression thesis: phases are just segments of one descent.
- Find the cleanest counterexample to "post-training is a different thing."
- Decide whether this is its own arXiv note or a section of the compression paper.
