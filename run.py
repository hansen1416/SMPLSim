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

def sample_betas_energy_uniform(
    batch_size: int,
    num_betas: int = 10,
    energy_max: float = 20.25,  # E_max = 4.5^2
    energy_min: float = 0.0,  # set = energy_max for fixed energy
    per_dim_clip: float = 3.0,
    rng: np.random.Generator = None,
) -> np.ndarray:
    """
    Sample SMPL betas with:
        - beta in R^{num_betas}
        - each component in [-per_dim_clip, per_dim_clip]
        - energy E = ||beta||^2 in [energy_min, energy_max]
        - directions uniform on the sphere
        - energy approximately uniform in [energy_min, energy_max]

    Args:
        batch_size: number of vectors to sample.
        num_betas: dimensionality (e.g. 10 or 16).
        energy_max: maximum energy (e.g. 20.25).
        energy_min: minimum energy (0 for full range; set equal to energy_max
                    if you want fixed energy).
        per_dim_clip: per-component bound (e.g. 3.0).
        rng: optional np.random.Generator.

    Returns:
        betas: (batch_size, num_betas) array.
    """
    if rng is None:
        rng = np.random.default_rng()

    collected = []

    def enough():
        return sum(x.shape[0] for x in collected) >= batch_size

    while not enough():
        # oversample to reduce the number of while-loop iterations
        n_try = max(batch_size - sum(x.shape[0] for x in collected), 1) * 8

        # 1) directions ~ uniform on sphere
        z = rng.standard_normal(size=(n_try, num_betas))
        norms = np.linalg.norm(z, axis=1, keepdims=True)
        # avoid division by zero
        norms[norms == 0.0] = 1.0
        dirs = z / norms

        # 2) energies: uniform in [energy_min, energy_max]
        E = rng.uniform(energy_min, energy_max, size=(n_try, 1))
        r = np.sqrt(E)

        # 3) construct candidates
        cand = dirs * r  # shape (n_try, num_betas)

        # 4) enforce per-dim constraint via rejection
        mask = np.all(np.abs(cand) <= per_dim_clip, axis=1)
        cand = cand[mask]

        if cand.size > 0:
            collected.append(cand)

    betas = np.concatenate(collected, axis=0)[:batch_size]
    # for smplsim, 4 decimal is good enough
    betas = np.round(betas, 4)
    return betas


def generate_yaml(betas: torch.Tensor, gender: Gender, name: str):
    """Generate a custom humanoid model and save it as an MJCF XML file.
    Args:
        betas (torch.Tensor): Shape parameters for the SMPL model, shape (1, 10).
        gender (str): Gender of the humanoid, one of 'male', 'female', 'neutral'.

    """

    robot_cfg = {
        "model": "smpl",
        "mesh": False,
        "sim": "isaacgym",
        "real_weight": True,
        "real_weight_porpotion_capsules": True,
        "real_weight_porpotion_boxes": True,
        # Optional: expose density
        # "geom_params": {"density": {"lb": [1000.0], "ub": [10.0]}},  # ~1000–1200 kg/m^3
    }

    smpl_robot = SMPL_Robot(robot_cfg)
    smpl_robot.load_from_skeleton(betas=betas, gender=[SMPLHumanoid.GENDER2NUM[gender]])

    output_folder = "output"

    output_path = os.path.join(
        output_folder, f"{name}_smpl.xml"
    )

    betas_path = os.path.join(
        output_folder, f"{name}_betas.pt"
    )

    # Export to MJCF
    smpl_robot.write_xml(output_path)
    print(f"Saved humanoid to {output_path}")

    torch.save(betas, betas_path)
    print(f"Saved humanoid betas to {betas_path}")

    # xml_string = smpl_robot.export_xml_string().decode("utf-8")

    # with open("custom_humanoid.xml", "w") as f:
    #     f.write(xml_string)


if __name__ == "__main__":

    num_betas: int = 10
    batch_size: int = 64
    per_dim_clip: float = 3.0
    energy_max: float = 20.25
    energy_min: float = 0.0

    rng = np.random.default_rng(46)

    all_betas = sample_betas_energy_uniform(
            batch_size=batch_size,
            num_betas=num_betas,
            per_dim_clip=per_dim_clip,
            energy_max=energy_max,
            energy_min=energy_min,
            rng=rng,
        )
    
    # print(all_betas.shape)

    # genders = ["male", "female", "neutral"]

    # # for gender in genders:
    for betas in all_betas:
        random_str = deterministic_hex4(rng)
        generate_yaml(torch.from_numpy(betas).unsqueeze(0), "neutral", random_str)
