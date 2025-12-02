Short answer: the 10 SMPL shape parameters are *global PCA modes* of body shape (not clean “body-part knobs”), and for shape-conditioned motion generation on typical adult data, using these 10 is standard and usually sufficient.

---

### 1. What do the 10 SMPL shape coefficients actually control?

Formally, SMPL models body shape as

[
v(\beta,\theta) = W\big(T(\beta,\theta), J(\beta), \theta, \mathcal{W}\big),
]

with

[
T(\beta,\theta) = \mathbf{T}*\text{template} + \sum*{i} \beta_i ,\mathbf{B}^s_i + \text{pose blend shapes},
]

where (\beta \in \mathbb{R}^{10}) and (\mathbf{B}^s_i) are the PCA shape basis vectors learned from CAESAR scans.

Consequences:

* Each **βᵢ affects all vertices**, not a single anatomical part.
* The 10 dimensions are **orthogonal PCA directions** in the training population, so they are “statistically optimal” but not cleanly interpretable as “only thighs” or “only arms”.

Empirically (from visualizations and follow-up analyses of SMPL/SMPL-X shape space):

* **β₁**: overall *height / limb length* (tall vs short, long vs short legs and arms).
* **β₂**: overall *girth / weight* (thin vs heavy, body mass around torso and limbs).
* **β₃**: *proportions* (e.g. longer legs vs longer torso, pelvis vs chest balance).
* **β₄–β₁₀**: more localized but still global patterns:

  * shoulder width and chest depth,
  * hip width and pelvis shape,
  * thigh/calf thickness,
  * belly / lower-back curvature, etc.

In other words, they primarily control:

* **Anthropometric measurements**: height, limb lengths, chest/waist/hip circumferences, etc.
* The **skeleton** implicitly, because SMPL joints are regressed from the shaped mesh (J(\beta)), so changing β changes segment lengths as well as the surface.

There is no official mapping like “β₃ = shoulder width”, but you can see the effect of each βᵢ by rendering (\beta_i = \pm 2) (others zero) and examining which regions grow/shrink.

---

### 2. Is β ∈ ℝ¹⁰ enough for *shape-conditioned motion generation*?

For most realistic setups: **yes, 10 is enough and is the de-facto standard**.

Arguments:

1. **Variance coverage / reconstruction accuracy**

   * SMPL’s PCA shape space is learned on thousands of CAESAR scans; using the first ≈10 components already captures the vast majority of adult body-shape variance with low mean per-vertex error (a few millimetres).
   * Many works explicitly use only 10 (or at most 16) betas and still obtain accurate anthropometric measurements and realistic meshes.

2. **Community practice in motion datasets**

   * AMASS stores SMPL shape as 16-D betas but is routinely truncated or used with 10-D shape codes in downstream models; 10-D SMPL is the canonical configuration in a lot of motion, pose-estimation, and regression work.
   * Shape-aware motion methods (e.g., using SMPL/SMPL-X on AMASS) generally condition only on these low-dimensional betas plus pose, and obtain realistic shape-dependent motion.

3. **What matters for motion**
   For *motion generation*, the critical shape effects are:

   * **Segment lengths and proportions** (leg length → step length, arm length → reach; torso vs leg proportion → gait).
   * **Global body size** (height, mass distribution) to avoid foot sliding, interpenetration, etc.

   These aspects are *exactly* what the first few betas encode and are already well captured by β₁…β₁₀.

   Fine-scale shape details (muscle definition, soft-tissue bulges, subtle obesity vs muscular differences) are more relevant for *appearance* or *soft-tissue simulation*, not for the kinematics your motion generator needs.

4. **Complexity vs. data**

   * Using more than 10–16 shape dimensions increases model capacity and data sparsity without strong evidence that it improves *motion quality* (as opposed to mesh details).
   * Many text-to-motion / motion-forecasting pipelines therefore stick with 10 betas as the shape code and put modelling capacity into temporal dynamics instead.

5. **When 10 might *not* be enough**

   You might want >10 (or additional shape terms) if:

   * You explicitly target **extreme or under-represented bodies** (very obese, bodybuilders, children, elderly, amputees), where the SMPL/CAESAR shape space itself is known to be limited.
   * You want **soft-tissue dynamics** (breasts, belly jiggle, etc.)—in that case, people typically add DMPL (8D) or related dynamic shape components on top of the 10 static betas.

   Even then, the base **β ∈ ℝ¹⁰** is usually kept and augmented rather than replaced.

---

### 3. Practical recommendation for your setup

For *shape-conditioned motion generation* with SMPL/SMPLsim:

* Represent each subject with **β ∈ ℝ¹⁰** (standard SMPL betas).
* Feed β (or a learned embedding of β) as the *shape condition* into your motion model.
* If your data include strong shape extremes *and* you care about them, consider:

  * using the **16-D AMASS betas** if your SMPL variant supports it, or
  * augmenting with a small number of **dynamic shape / DMPL** parameters for soft tissue.

But unless you have a very specific reason and enough data, **staying with 10 betas is a very reasonable and widely accepted choice** for shape-aware motion generation.
