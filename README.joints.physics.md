Below are the **MJCF properties that affect joint motion** (i.e., they change the equations of motion, constraints, contact forces, or numerical integration). I list them by *where they live* in the XML.

## 1) Joint / DoF passive dynamics (directly changes joint torques/accelerations)

MuJoCo distinguishes **DoF (velocity-related)** vs **joint (position-related)** properties; these are the main ones. ([MuJoCo Docs][1])

### `<joint ...>`

* `damping` *(DoF)*: viscous torque ∝ joint velocity.
* `armature` *(DoF)*: adds inertia in generalized coordinates (stabilizes / changes acceleration response).
* `frictionloss` *(DoF, not in your snippet but important)*: Coulomb-like velocity-sign friction at the DoF level. ([MuJoCo Docs][1])
* `stiffness` *(joint)*: passive spring torque toward `springref`.
* `springref` *(joint, not in your snippet)*: equilibrium position for the joint spring.
* `limited`, `range` *(joint)*: hard/soft-limited joint coordinates (affects reachable motion + limit forces). ([MuJoCo Docs][1])
* **limit/contact solver tuning (often used, not in your snippet):** `solreflimit`, `solimplimit`, `solreffriction`, `solimpfriction` (how “soft” joint-limit and friction constraints are).

## 2) Inertia / mass distribution (changes how easily joints accelerate)

### `<inertial ...>` *(not present in your snippet, but highest priority if used)*

* `mass`, `diaginertia` / `fullinertia`, `ipos`, `iquat`: directly set rigid-body inertial properties.

### `<geom ...>` (in your model, inertia is inferred from geoms because you give `density`)

* `density`: used (with geom volume) to compute mass and inertia at compile time.
* `type`, `size`, `fromto`: define shape/volume and inertia.
* `pos`, `quat`: shift/rotate the geom relative to the body, changing inertia tensor about joints.

### `<compiler ...>` (affects how inertia is produced/regularized at compile time)

* `inertiafromgeom`: whether/when inertial properties are inferred from geoms.
* `boundmass`, `boundinertia`: lower-bounds on mass/inertia (numerical + physical impact).
* `settotalmass`: rescales masses to a desired total.
* `balanceinertia`: inertia regularization for stability. ([MuJoCo Docs][2])

## 3) Actuation (how control becomes joint torque/force)

### `<actuator> <motor .../>`

* `joint="..."`: which DoF is actuated.
* `gear`: transmission scaling from control/actuator space to joint torque. (You set `gear="500"` everywhere.)

Common actuator properties that strongly affect joint motion (not in your snippet but frequently used):

* `ctrlrange`: clamps control input. ([MuJoCo Docs][3])
* `forcerange`: clamps actuator output force/torque. ([MuJoCo Docs][3])
* `lengthrange`: relevant for muscles (feasible actuator length range). ([MuJoCo Docs][3])
* Servo/activation dynamics (depending on actuator type): `gainprm`, `biasprm`, `dyntype`, `dynprm`, plus actuator state limits (`actlimited`, `actrange`).

### `<joint actuatorfrcrange="...">` *(not in your snippet)*

* `actuatorfrcrange`: clamps the **sum** of actuator forces applied to a joint (post-transmission). ([MuJoCo Docs][3])

## 4) Contact (ground interaction strongly changes legged joint trajectories)

### `<geom ...>` contact/friction/solver parameters

* `condim`: number of friction directions in the contact model (normal-only vs with tangential/rolling/torsional components).
* `friction` *(not in your snippet)*: friction coefficients (sliding / torsional / rolling, depending on `condim`).
* `solref`, `solimp` *(not in your snippet)*: contact constraint softness/impedance (affects bounciness/penetration/settling).
* `margin`: contact activation distance (affects when contact constraints engage).
* `contype`, `conaffinity`: collision filtering (whether contacts exist at all).

### `<contact> <exclude .../>`

* `exclude body1 body2`: removes self-contacts, which can otherwise produce large constraint forces and alter motion.

## 5) Global physics + solver/integration (changes *every* joint trajectory)

### `<option ...>` *(not in your snippet, but decisive)*

* `timestep`: integration step size.
* `integrator`: numerical integrator choice.
* `solver`: constraint solver type.
* `iterations`, `ls_iterations`, `noslip_iterations`, plus tolerances (`tolerance`, `ls_tolerance`, `noslip_tolerance`, …).
* `gravity`: global gravity vector.
* `density`, `viscosity`, `wind`: fluid/drag effects (if enabled/used). ([MuJoCo Docs][2])

## 6) Capacity limits that can indirectly change motion (by dropping contacts/constraints)

### `<size ...>`

* `nconmax`: max number of contacts stored; too low can drop contacts → different joint motion.
* `njmax`: max constraints; too low can truncate constraints. ([MuJoCo Docs][2])

[1]: https://mujoco.readthedocs.io/en/2.3.7/overview.html?utm_source=chatgpt.com "Overview - MuJoCo Documentation"
[2]: https://mujoco.readthedocs.io/en/stable/XMLreference.html "XML Reference - MuJoCo Documentation"
[3]: https://mujoco.readthedocs.io/en/stable/modeling.html "Modeling - MuJoCo Documentation"
