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

  ---
  3. Fixed body hierarchy

  Correct. The hierarchy is fixed by parents_dict from SMPL topology, e.g.:
  Pelvis → Torso → Spine → Chest → Neck → Head
                          → L_Thorax → L_Shoulder → L_Elbow → L_Wrist → L_Hand
           → L_Hip → L_Knee → L_Ankle → L_Toe
  This is passed into load_from_offsets and determines the nested <body> structure in the XML.

  ---

  4. Geom inside body, spanning between joint positions
  
  Correct. In write_xml_bodynode (line 565–735), a single <geom> is written as a child of each <body>. For capsules (most
  limbs), fromto defines the two endpoints:
  e1 = np.zeros(3)       # at current joint (body origin)
  e2 = bone.end.copy()   # toward child joint (mean of children's offsets)
  e1 += e2 * separation  # shrunk inward slightly (0.2 or 0.6 for trunk)
  e2 -= e2 * separation
  g_attr["fromto"] = ...  # capsule from e1 to e2
  So the geom spans between (not exactly at) adjacent joint positions.

    - bone.pos — the start point (where this joint is, i.e. where the body connects to its parent)
  - bone.end — the end point (mean of children's positions, i.e. where the next joint is)

  These two points define the segment that the geom must fit inside. You can see this directly in write_xml_bodynode at line
  588:

  e1 = np.zeros(3)         # origin of current body = bone.pos in local frame
  e2 = bone.end.copy() + offset   # toward child joint

  Then inset slightly from both ends:
  e1 += e2 * separation    # move away from joint (0.2, or 0.6 for trunk)
  e2 -= e2 * separation

  So e1 and e2 are the two endpoints of the available space, and then:

  - For capsule: fromto = [e1, e2] — capsule axis runs between them, radius is solved from hull_dict[bone.name].volume
  - For box: pos = (e1 + e2) / 2, size derived from hull_dict
  - For sphere: pos = origin, radius from hull_dict

  So bone.pos → bone.end is the space, and hull_dict[bone.name].volume is the volume constraint that determines how thick the
  geom is within that space.



  ● The order in construct_tree makes it clear:

  1. write_xml_bodynode runs first (line 412) — writes all bodies, geoms, joints into the XML tree based purely on
  bone.pos/bone.end/hull_dict volume. At this point geoms may overlap each other.
  2. geom_clearance.py runs after (lines 455–472) — it operates as a post-processing pass on the already-written XML:
    - collect_geoms_from_tree(tree) — reads all geoms back out of the XML
    - build_adjacency(self.bones) — finds which body pairs are adjacent (parent-child) so they're excluded from clearance
  checks
    - enforce_clearance(geoms, adj, min_gap) — shrinks any geom radii that are too close to a non-adjacent geom
    - apply_geoms_to_tree(geoms) — writes the adjusted sizes back into the XML

  So geom_clearance.py doesn't decide geom positions or shapes — it only shrinks geom radii after the fact if non-adjacent
  geoms are overlapping or too close. write_xml_bodynode still makes all the primary decisions; clearance enforcement is
  purely a correction pass on top.



  ---
  5. Geom encodes mass/inertia
  
  Partially correct — with an important nuance. There is no explicit <inertial> element written. Instead, each geom has a
  density attribute (default 500 kg/m³, or 1000 if real_weight=True):
  g_attr["density"] = str(base_density)
  MuJoCo automatically derives the body's mass and inertia tensor from the geom's shape + density when no explicit <inertial>
  block is present. So the geom implicitly carries inertial information — not as a sub-element, but via density on the geom
  itself.
