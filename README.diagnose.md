## Summary of findings (Good 52 vs Bad 12)

### 1) Contact/friction is not the differentiator

* The **friction/contact parameterization is effectively constant** across all MJCF templates.
* Therefore, the instability is **not** explained by contact settings, but by **geometry / kinematics / mass–inertia effects** induced by shape.

### 2) What differs in the MJCF geometry (derived from templates)

* Across the full sets, mean differences in many single measurements are small, but the **bad set has much larger variance and more extremes**.

* The most diagnostic geometric/scale features were:

  * **Foot support / ankle box dimensions**: bad templates tend to include more extreme (especially smaller) ankle/foot sizes.
  * **Trunk thickness (Spine/Torso radii)**: bad set includes **very thin** and **very thick** trunks relative to good.
  * **Global scale proxies** (pelvis radius, average capsule radius, limb lengths): bad contains **outliers** beyond the good range.

* Clear “extreme-shape” cases exist in the bad set:

  * One **very small** body (low pelvis/trunk radii, small feet) with very low estimated mass ((\sim 35) kg).
  * One **very large** body (large pelvis/trunk radii, large feet) with very high estimated mass ((\sim 131) kg).

* Several bad templates fall **outside the good range** in multiple features simultaneously (especially feet + trunk radii), consistent with scale/inertia mismatch causing instability under fixed gains.

### 3) What differs in the SMPL betas (directly from your lists)

* There is **no clean single-dimension threshold** that separates all bad from all good.
* However, bad betas are more **out-of-distribution (OOD)** in magnitude and multivariate combination:

  * Bad has higher **L2 norm** and higher **max-abs** on average.
  * Bad has more coordinates with (|\beta_i|>2).
  * Using the good distribution as reference, **Mahalanobis distance** shows many bad betas are strongly OOD:

    * ~**7/12** bad exceed the good **95th percentile** OOD score.
    * ~**6/12** bad exceed the good **99th percentile** and even the **maximum** observed in good.
* The strongest single-coordinate “red flag” is **(\beta_0)**:

  * Bad has several samples with (\beta_0) outside the entire good range.

### 4) Interpretation for IsaacGym RL instability

* Evidence points to instability being driven by **morphology extremes / OOD shapes** → altered **collision geometry, mass/inertia**, and **effective control gains** (when gains/actuation are fixed across morphologies), rather than friction/contact tuning.

### 5) Practical diagnostic gates (useful for debugging)

* A fast way to identify many problematic shapes is to filter for **OOD betas** (e.g., Mahalanobis distance to the good beta distribution) and/or **(\beta_0)** out-of-range.
* These simple gates catch **most** bad cases in your sample; remaining failures may come from **beta→MJCF mapping edge cases** (e.g., inertia scaling, collision geom sizing, joint limit interactions), not from betas alone.
