1. Positions read from SMPL model → local offsets

In smpl_parser.py:174:

```python
joint_offsets = {joint_names[c]: (joint_pos[c] - joint_pos[p]) if c > 0 else joint_pos[c] for c, p in enumerate(smpl_joint_parents)}
```

{'Pelvis': tensor[3], 'L_Hip': tensor[3], 'R_Hip': tensor[3], 'Torso': tensor[3], 'L_Knee': tensor[3], 'R_Knee': tensor[3], 'Spine': tensor[3], 'L_Ankle': tensor[3], 'R_Ankle': tensor[3], 'Chest': tensor[3], 'L_Toe': tensor[3], 'R_Toe': tensor[3], 'Neck': tensor[3], 'L_Thorax': tensor[3], 'R_Thorax': tensor[3], 'Head': tensor[3], 'L_Shoulder': tensor[3], 'R_Shoulder': tensor[3], 'L_Elbow': tensor[3], 'R_Elbow': tensor[3], 'L_Wrist': tensor[3], 'R_Wrist': tensor[3], 'L_Hand': tensor[3], 'R_Hand': tensor[3]}  

each is local offset from parent except Pelvis
Each offset = child joint position − parent joint position in the zero-pose.
            
parents_dict = {joint_names[i]: joint_names[parents[i]] for i in range(len(joint_names))}

{'Pelvis': 'R_Hand', 'L_Hip': 'Pelvis', 'R_Hip': 'Pelvis', 'Torso': 'Pelvis', 'L_Knee': 'L_Hip', 'R_Knee': 'R_Hip', 'Spine': 'Torso', 'L_Ankle': 'L_Knee', 'R_Ankle': 'R_Knee', 'Chest': 'Spine', 'L_Toe': 'L_Ankle', 'R_Toe': 'R_Ankle', 'Neck': 'Chest', 'L_Thorax': 'Chest', 'R_Thorax': 'Chest', 'Head': 'Neck', 'L_Shoulder': 'L_Thorax', 'R_Shoulder': 'R_Thorax', 'L_Elbow': 'L_Shoulder', 'R_Elbow': 'R_Shoulder', 'L_Wrist': 'L_Elbow', 'R_Wrist': 'R_Elbow', 'L_Hand': 'L_Wrist', 'R_Hand': 'R_Wrist'}
 
skin_weights = self.lbs_weights.numpy()
(6890, 24) define the rigging, it's the source of the hull_dict, which is what determines geom sizes.

------

2. Local offsets define child joint positions (limb lengths)

load_from_offsets in smpl_sim/smpllib/skeleton_local.py

- joint_offsets — passed into load_from_offsets unchanged. The symmetry-enforcement block that would modify it is commented
  out (lines 1461–1468).
- parents_dict — passed in unchanged.
- skin_weights — never passed into load_from_offsets at all. It's consumed by get_geom_dict() on line 1449–1453, which
produces self.hull_dict. Only hull_dict goes into load_from_offsets, not skin_weights itself.

  Correct. In skeleton_local.py:364:
  bone.offset = np.array(offsets[joint]) * self.len_scale
  Then forward_bvh (line 294) sets bone.pos = bone.offset — the body's pos attribute in the XML is this local offset from its
  parent. This directly encodes the limb geometry.

------

3. Fixed body hierarchy

Correct. The hierarchy is fixed by parents_dict from SMPL topology, e.g.:
Pelvis → Torso → Spine → Chest → Neck → Head
                        → L_Thorax → L_Shoulder → L_Elbow → L_Wrist → L_Hand
          → L_Hip → L_Knee → L_Ankle → L_Toe
This is passed into load_from_offsets and determines the nested <body> structure in the XML.

------

4. Geom inside body, spanning between joint positions

write_xml_bodynode (skeleton_local.py:563–609) writes one <geom> per <body>. Key quantities:
- bone.pos: body origin = current joint (local frame origin)
- bone.end: vector toward child joint
- radius (capsule): solved from hull_dict[bone.name].volume via capsule volume equation (lines 566–568)
- box: pos = midpoint of e1/e2, size from hull_dict norm_verts
- sphere: radius = cbrt(3V/4π)
- density on geom (default 500, or 1000 if real_weight) — MuJoCo derives mass/inertia automatically

The old approach inset fromto endpoints by a fixed separation fraction (0.2, or 0.6 for trunk) of bone length.
Problem: visible surface gap = axis_gap − radius_parent − radius_child. Since radii scale with body volume
(betas), thin bodies got large gaps and fat bodies got near-zero/overlapping gaps.

Fix (skeleton_local.py:595–608): after solving radius, recompute e1/e2 so the capsule surface lands at a
fixed desired_gap (default 0.03 m) from each joint:
  e1 = bone_dir * (radius + actual_gap)
  e2 = bone_vec − bone_dir * (radius + actual_gap)
actual_gap is clamped down gracefully for short bones so the capsule never becomes degenerate (zero-length),
with a final fallback placing a minimal 2 mm capsule at the bone midpoint.

------

5. Geom encodes mass/inertia

- Geom clearance gap

> We enforce a fixed minimum clearance between non-adjacent collision geoms to prevent morphology-dependent self-penetration caused by extreme SMPL body shapes.

GAINS_PHC in smpl_sim/smpllib/skeleton_local.py, Format: [stiffness, damping, gear, max_torque]

GAINS_PHC = {
      "L_Hip":      [800, 80, 1, 500],   # stiffness, damping written into <joint>
      "L_Knee":     [800, 80, 1, 500],   # gear written into <motor>
      ...
      "Torso":      [1000, 100, 1, 500],
      "L_Wrist":    [300, 30, 1, 150],
}


````markdown
## Physics Argument

Joint stiffness and damping act as PD gains in Isaac Gym. The closed-loop natural frequency of a PD-controlled joint is:

\[
\omega_n = \sqrt{\frac{k_p}{I}}
\]

With `real_weight=True`, density doubles: 500 → 1000 kg/m³

Therefore, body-segment inertia roughly doubles. With the same (k_p), the natural frequency drops by:

[
\frac{1}{\sqrt{2}} \approx 0.7
]

This means the controller becomes approximately **30% slower** at tracking.

For a critically damped response, the damping ratio is:

[
\zeta = \frac{k_d}{2\sqrt{k_p I}}
]

If (k_p) and (I) both double but (k_d) stays the same, then:

[
\zeta \rightarrow \frac{1}{\sqrt{2}} \zeta
]

So the system becomes more underdamped and may oscillate.

To preserve the same control bandwidth and damping ratio, both gains should scale proportionally with inertia: x2

### Argument for Scaling Gains by ×2

- Scaling the gains is more physically principled. If the model now represents a realistic human body mass, approximately **70–80 kg**, then the joint gains should reflect the increased inertial load.
- Published work (e.g., PHC, AMP) that achieves good AMASS tracking typically uses gains in the range of 1000–2000 for large joints at realistic human mass
- Underdamped joints cause oscillation artifacts visible in the simulation that affect motion quality metrics

