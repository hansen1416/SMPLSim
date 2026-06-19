"""Generate held-out SMPL body shapes for evaluation.

Produces beta vectors and humanoid XML templates that were NOT seen during
training, used for the E7 generalisation experiment in the paper.

Two modes
---------
interp  Interpolation: uniform[-3, 3] per dim, different seed from training.
        Tests in-distribution generalisation (same range, unseen samples).

extrap  Extrapolation: uniform[-5, 5] per dim, different seed.
        Produces shapes with systematically larger L2 norms (~9.1 vs ~5.5 for
        training), clearly outside the training envelope.

Output
------
Betas  : /home/hlz/repos/humos/humos/all_betas_{mode}.pt
XMLs   : protomotions/data/assets/mjcf/smpl_mor_{mode}/*.xml

After running this script, generate assets.yaml with:

    python tools/generate_smpl_mor_asset_info.py \\
        --asset-folder mjcf/smpl_mor_{mode} \\
        --betas-file /home/hlz/repos/humos/humos/all_betas_{mode}.pt \\
        --out protomotions/data/assets/mjcf/smpl_mor_{mode}/assets.yaml
"""

import argparse
import os
from typing import Literal

import numpy as np
import torch

from smpl_sim.smpllib.smpl_local_robot import SMPL_Robot
from smpl_sim.envs.smplenv import SMPLHumanoid

Gender = Literal["male", "female", "neutral"]

PROTOMOTIONS_ROOT = os.path.join(os.path.dirname(__file__), "../ProtoMotions")
BETAS_DIR = os.path.join(os.path.dirname(__file__), "../humos/humos")


def deterministic_hex4(rng: np.random.Generator) -> str:
    n = rng.integers(0, 2**32, dtype=np.uint32)
    return int(n).to_bytes(4, "big").hex()


def sample_betas(
    mode: str,
    num_betas: int,
    num_dims: int,
    rng: np.random.Generator,
) -> dict:
    """Sample beta vectors according to mode.

    interp: uniform[-3, 3] — same range as training (seed 46), new samples.
    extrap: uniform[-5, 5] — wider range; L2 norms ~9 vs ~5.5 for training.
    """
    if mode == "interp":
        low, high = -3.0, 3.0
    elif mode == "extrap":
        low, high = -5.0, 5.0
    else:
        raise ValueError(f"Unknown mode: {mode!r}. Choose 'interp' or 'extrap'.")

    raw = rng.uniform(low=low, high=high, size=(num_betas, num_dims))

    result = {}
    for i in range(num_betas):
        key = deterministic_hex4(rng)
        result[key] = torch.as_tensor(raw[i], dtype=torch.float32)

    return result


def generate_xml(betas: torch.Tensor, gender: Gender, name: str, output_folder: str) -> None:
    """Generate a MuJoCo XML humanoid for the given betas and save it."""
    robot_type = "smpl"

    robot_cfg = {
        "model": robot_type,
        "sim": "isaacgym",
        "mesh": False,
        "box_body": True,
        "replace_feet": True,
        "remove_toe": True,
        "big_ankle": False,
        "freeze_hand": True,
        "ball_joint": False,
        "rel_joint_lm": False,
        "upright_start": True,
        "real_weight": True,
        "real_weight_porpotion_capsules": True,
        "real_weight_porpotion_boxes": True,
        "create_vel_sensors": False,
        "body_params": {},
        "joint_params": {},
        "geom_params": {},
        "actuator_params": {},
    }

    smpl_robot = SMPL_Robot(robot_cfg)
    smpl_robot.load_from_skeleton(betas=betas, gender=[SMPLHumanoid.GENDER2NUM[gender]])

    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, f"{gender}_{name}_{robot_type}.xml")
    smpl_robot.write_xml(output_path)
    print(f"  saved {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate held-out SMPL betas and humanoid XML templates.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["interp", "extrap"],
        required=True,
        help=(
            "interp: uniform[-3,3], new seed — in-distribution held-out shapes. "
            "extrap: uniform[-5,5], new seed — out-of-distribution shapes."
        ),
    )
    parser.add_argument(
        "--num-betas",
        type=int,
        default=16,
        help="Number of new beta vectors to generate (× 2 genders = total XML files).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=99,
        help="RNG seed. Must differ from training seed (46).",
    )
    parser.add_argument(
        "--num-dims",
        type=int,
        default=10,
        help="Number of SMPL beta dimensions.",
    )
    parser.add_argument(
        "--genders",
        nargs="+",
        default=["male", "female"],
        help="Genders to generate XML files for.",
    )
    args = parser.parse_args()

    if args.seed == 46:
        raise ValueError(
            "Seed 46 is used for the training betas. Use a different seed "
            "(default: 99) to ensure the held-out shapes are truly unseen."
        )

    rng = np.random.default_rng(args.seed)

    # ------------------------------------------------------------------ #
    # 1. Sample betas
    # ------------------------------------------------------------------ #
    print(f"\n[1/3] Sampling {args.num_betas} held-out betas (mode={args.mode}, seed={args.seed})")
    all_betas = sample_betas(args.mode, args.num_betas, args.num_dims, rng)

    vals = torch.stack(list(all_betas.values()))
    norms = vals.norm(dim=1)
    print(f"      L2 norms — min: {norms.min():.2f}, max: {norms.max():.2f}, mean: {norms.mean():.2f}")
    print(f"      per-dim  — min: {vals.min():.2f}, max: {vals.max():.2f}")

    # ------------------------------------------------------------------ #
    # 2. Save betas
    # ------------------------------------------------------------------ #
    betas_path = os.path.join(BETAS_DIR, f"all_betas_{args.mode}.pt")
    torch.save(all_betas, betas_path)
    print(f"\n[2/3] Betas saved to: {betas_path}")

    # ------------------------------------------------------------------ #
    # 3. Generate XML assets
    # ------------------------------------------------------------------ #
    output_folder = os.path.join(
        PROTOMOTIONS_ROOT,
        f"protomotions/data/assets/mjcf/smpl_mor_{args.mode}",
    )
    print(f"\n[3/3] Generating XML templates → {output_folder}")

    total = len(all_betas) * len(args.genders)
    done = 0
    for beta_key, betas_tensor in all_betas.items():
        for gender in args.genders:
            generate_xml(betas_tensor.unsqueeze(0), gender, beta_key, output_folder)
            done += 1

    print(f"\nDone. Generated {done}/{total} XML files.")
    print(
        f"\nNext step — generate assets.yaml:\n"
        f"  cd /home/hlz/repos/ProtoMotions\n"
        f"  python tools/generate_smpl_mor_asset_info.py \\\n"
        f"      --asset-folder mjcf/smpl_mor_{args.mode} \\\n"
        f"      --betas-file {betas_path} \\\n"
        f"      --out protomotions/data/assets/mjcf/smpl_mor_{args.mode}/assets.yaml"
    )


if __name__ == "__main__":
    main()
