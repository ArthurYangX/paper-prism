# Concept Auto-Categorization Rules

Concept library location: `{CONCEPTS_PATH}`

First run `ls {CONCEPTS_PATH}` to see the existing subfolders, then categorize using the table below.

> Localize these folder names freely; they're a starting taxonomy, not a contract.

| Subfolder | Categorization criteria | Examples |
|-----------|-------------------------|----------|
| `1-generative-models` | Diffusion models, GAN, VAE, Flow, generation-related methods | DMD, DPM-Solver, SDE, NFE, Score Distillation |
| `2-reinforcement-learning` | RL algorithms, policy optimization, value functions, reward | Actor-Critic, PPO, MBRL, CRL, DrQv2, DAPG |
| `3-robot-policy` | Manipulation policies, grasping, dexterous hands, imitation learning, VLA | HOI, DexRep, UniDexGrasp, Diffusion Policy |
| `4-legged-locomotion` | Quadruped, biped, locomotion | CPG, Raibert Controller |
| `5-navigation-and-localization` | SLAM, path planning, navigation | NAVSIM, VPR |
| `6-3d-vision` | NeRF, 3DGS, point clouds, depth estimation, stereo vision | Epipolar Geometry, 4DGS |
| `7-planning-and-control` | Control theory, optimizers, MPC, PID | PID, SMC, ILC, OSQP, CVXPY, SNOPT |
| `8-simulators` | Simulation platforms, physics engines | IsaacLab, MuJoCo |
| `9-drones` | UAV, flight control | PX4 |
| `10-datasets` | Datasets, benchmarks | ImageNet, YCB, BridgeV2, FFHQ |
| `11-deep-learning-foundations` | General DL techniques, architecture components, training tricks | GMM, EMA, MoE, GAT, Transformer, Teacher Forcing |
| `12-physics-simulation` | Physics models, biomechanics simulation | OpenSim, SCONE, FEM |
| `13-robot-hardware` | Sensors, actuators, robot platforms | Tendon Drive, Tactile Sensor |
| `14-safety-and-robustness` | Adversarial attacks, safety constraints | CBF, Adversarial |
| `15-web-agents` | Web operation, browser automation | WebAgent |
| `16-human-motion` | Human pose, motion generation, motion capture | ViTPose, SMPL, Motion Capture |
| `17-continual-learning` | CIL / Class-Incremental, Replay, Regularization, Prompt-based CL | iCaRL, EWC, LwF, FOSTER, RanPAC, FeTrIL, FeCAM, DualPrompt, CodaPrompt, SLCA |
| `18-state-space-models` | SSM / Mamba family, long-sequence modeling | S4, S6, Selection Mechanism, Parallel Scan, HiPPO, ZOH Discretization, VMamba |
| `19-hyperspectral-remote-sensing` | Hyperspectral image classification, multispectral, SAR, remote-sensing fusion | Hyperspectral Image, HSI Classification, Spectral Attention, MUUFL, S2ENet |
| `20-multimodal-fusion` | Cross-modal alignment, modality fusion, inter-modal compensation | Cross-Modal Attention, Modality Fusion, FuSatNet, X-Net |
| `0-uncategorized` | **Use only when categorization is truly impossible**; avoid as much as possible | — |

## Concept creation budget (prevents explosion during batch processing)

**Create at most `cfg.concept_budget` (default 8) new concept notes per paper** — always, not only for large batches; `plan_concepts()` enforces it deterministically and downgrades the overflow to bold:

1. Scan all `[[concept]]` links in the note → deduplicate
2. Check each concept in the following order:
   - Already exists (exact filename match) → **reuse**
   - Existing alias (frontmatter `aliases` hit) → **reuse + change this note's link to `[[CanonicalName|wording used in this paper]]`**
   - Fuzzy match (lowercase + strip spaces/hyphens + Levenshtein ≤ 2) → warn "possible duplicate name" and let the main agent decide
   - Brand-new concept → create
3. When the per-paper new-concept count > 8:
   - Sort by "number of occurrences in the note" and **create only the top 8**
   - Demote the rest to bold `**concept name**` (no wiki link, to avoid red links)
   - Add a `## Concepts not yet created` section at the end of the main note listing the follow-ups
4. After the batch finishes, regenerate the index (run the concept MOC generator)

⚠️ **Duplicate-name pitfalls (frequent in batch scenarios)**:
- `Mamba` vs `Mamba SSM` vs `Selective SSM` → all alias to `Selection Mechanism` or `Mamba` (pick the more general one)
- `Class-Incremental Learning` vs `CIL` vs `类别增量学习` → alias to `Class-Incremental Learning`
- `EWC` vs `Elastic Weight Consolidation` → alias to `Elastic Weight Consolidation`
- Singular / plural / different tense: `Knowledge Distillation` vs `Knowledge Distillations` → normalize to the singular form

## Concept note template

```markdown
---
type: concept
aliases: [alias-1, alias-2]
---

# Concept Name

## Definition
{one-sentence definition}

## Mathematical form
$$formula$$

## Core points
1. ...
2. ...

## Representative works
- [[Paper1]]: ...
- [[Paper2]]: ...

## Related concepts
- [[Related concept 1]]
- [[Related concept 2]]
```
