import os
import random
from typing import Literal
import numpy as np

from smpl_sim.smpllib.smpl_local_robot import SMPL_Robot
from smpl_sim.envs.smplenv import SMPLHumanoid
import torch

Gender = Literal["male", "female", "neutral"]

def deterministic_hex4(rng: np.random.Generator):
    n = rng.integers(0, 2**32, dtype=np.uint32)
    return int(n).to_bytes(4, "big").hex()

def sample_betas_uniform(
    batch_size: int,
    num_betas: int = 10,
    low: float = -2.0,
    high: float = 2.0,
    rng: np.random.Generator = None,
) -> np.ndarray:
    """
    Sample SMPL / SMPL-X betas from a uniform distribution in the interval [low, high].

    This gives the most even coverage of the shape space within the chosen bounds.
    Useful when:
    - you want to avoid the clustering around zero that happens with normal sampling
    - you want predictable / reproducible diversity across the full selected range
    - you're testing physics stability across many shape variations

    Recommended ranges (2025–2026 practice):
      [-2.0, 2.0]   → very safe, mostly natural bodies
      [-2.5, 2.5]   → good diversity, still quite stable in Isaac Gym / MJX
      [-3.0, 3.0]   → noticeable extremes, expect ~5–15% unstable bodies
      [-3.5, 3.5]   → aggressive — many interpenetrating / exploding cases

    Args:
        batch_size: Number of beta vectors to generate
        num_betas: Usually 10 (SMPL) or 10–16 (SMPL-X)
        low: Lower bound of the uniform interval
        high: Upper bound of the uniform interval (must be > low)
        rng: Optional numpy random generator for reproducibility

    Returns:
        betas: shape (batch_size, num_betas), dtype float32
    """

    if high <= low:
        raise ValueError("high must be strictly greater than low")

    # Uniform sampling in [low, high]
    betas = rng.uniform(low=low, high=high, size=(batch_size, num_betas))

    all_betas = {}

    for i in range(betas.shape[0]):
        random_str = deterministic_hex4(rng)

        all_betas[random_str] = torch.as_tensor(betas[i], dtype=torch.float32)

    # for smplsim, 4 decimal is good enough
    # betas = np.round(betas, 4)
    return all_betas


def generate_yaml(betas: torch.Tensor, gender: Gender, name: str):
    """Generate a custom humanoid model and save it as an MJCF XML file.
    Args:
        betas (torch.Tensor): Shape parameters for the SMPL model, shape (1, 10).
        gender (str): Gender of the humanoid, one of 'male', 'female', 'neutral'.

    """

    robot_cfg = {
        "model": "smpl",              # fewer bodies/joints than smplx → fewer self-collisions
        "sim": "isaacgym",

        "mesh": False,                # avoid mesh/convex-hull contacts
        "box_body": False,            # boxes create sharp-edge contact explosions in PhysX
        "replace_feet": True,         # simplify feet collision proxy
        "remove_toe": True,           # toes are a frequent instability source
        "big_ankle": False,           # reduces ankle-shin interpenetration risk
        "freeze_hand": True,          # (SMPL: mostly irrelevant; harmless)

        "ball_joint": False,          # keep simpler joint model
        "rel_joint_lm": False,        # keep default joint limits (avoid “too-loose” joints)
        "upright_start": True,       # keep default construction pose

        "real_weight": False,          # more reasonable mass/inertia distribution
        "real_weight_porpotion_capsules": False,
        "real_weight_porpotion_boxes": False,

        "create_vel_sensors": False,

        # do NOT randomize geometry/joints at first
        "body_params": {},
        "joint_params": {},
        "geom_params": {},
        "actuator_params": {},
    }

    smpl_robot = SMPL_Robot(robot_cfg)
    smpl_robot.load_from_skeleton(betas=betas, gender=[SMPLHumanoid.GENDER2NUM[gender]])

    output_folder = "/home/hlz/repos/ASE/ase/data/assets/mjcf/smpl/"

    output_path = os.path.join(
        output_folder, f"{gender}_{name}_smpl.xml"
    )

    # betas_path = os.path.join(
    #     output_folder, f"{name}_betas.pt"
    # )

    # Export to MJCF
    smpl_robot.write_xml(output_path)
    print(f"Saved humanoid to {output_path}")

    # torch.save(betas, betas_path)
    # print(f"Saved humanoid betas to {betas_path}")

    # xml_string = smpl_robot.export_xml_string().decode("utf-8")

    # with open("custom_humanoid.xml", "w") as f:
    #     f.write(xml_string)


if __name__ == "__main__":

    rng = np.random.default_rng(46)

    all_betas = sample_betas_uniform(
            batch_size=64,
            num_betas=10,
            low = -3.0,
            high = 3.0,
            rng=rng,
        )

    save_paths = [os.path.join("/home/hlz/repos/humos/humos/all_betas.pt"),
                  os.path.join("/home/hlz/repos/ASE/ase/data/assets/all_betas.pt")]

    for save_path in save_paths:
        torch.save(all_betas, save_path)

    # # for gender in genders:
    for beta_key, betas in all_betas.items():
        for gender in ["male", "female"]:
            # random_str = deterministic_hex4(rng)
            generate_yaml(betas.unsqueeze(0), gender, beta_key)

            print(f"- mjcf/smpl/{gender}_{beta_key}_smpl.xml")

    # for n in random_names:
    #     print(f"- mjcf/smpl/{n}_smpl.xml")
