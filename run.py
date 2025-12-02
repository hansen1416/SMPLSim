import os
from datetime import datetime
from typing import Literal

from smpl_sim.smpllib.smpl_local_robot import SMPL_Robot
from smpl_sim.envs.smplenv import SMPLHumanoid
import torch

Gender = Literal["male", "female", "neutral"]


def generate_taml(betas: torch.Tensor, gender: Gender):
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

    # generate a random string to avoid overwriting files
    random_str = os.urandom(4).hex()

    output_path = os.path.join(
        output_folder, f"custom_simple2_{gender}_{random_str}.xml"
    )

    # Export to MJCF
    smpl_robot.write_xml(output_path)
    print(f"Saved humanoid to {output_path}")

    # xml_string = smpl_robot.export_xml_string().decode("utf-8")

    # with open("custom_humanoid.xml", "w") as f:
    #     f.write(xml_string)


if __name__ == "__main__":

    # # Average neutral body
    # betas = torch.zeros((1, 10))

    # # Shorter, stockier body
    # betas = torch.tensor([[-1.5, -0.5, 0.2, 0, 0, 0, 0, 0, 0, 0]])

    # # Very tall, slim body
    # betas = torch.tensor([[2.5, 1.0, 0.5, 0, 0, 0, 0, 0, 0, 0]])

    # # Random natural variation
    # betas = torch.randn(1, 10) * 0.5  # normal distribution, mild variation

    # # More extreme stylized character
    # betas = torch.tensor([[3.0, -2.0, 1.5, 0.5, 0, 0, 0, 0, 0, 0]])

    # # Slightly taller, leaner body
    # betas = torch.tensor([[0.9, 0.9, 0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])

    all_betas = [
        torch.zeros((1, 10)),
        # torch.tensor([[-1.5, -0.5, 0.2, 0, 0, 0, 0, 0, 0, 0]]),
        # torch.tensor([[2.5, 1.0, 0.5, 0, 0, 0, 0, 0, 0, 0]]),
        # torch.randn(1, 10) * 0.5,
        # torch.tensor([[3.0, -2.0, 1.5, 0.5, 0, 0, 0, 0, 0, 0]]),
        # torch.tensor([[0.9, 0.9, 0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]),
    ]

    genders = ["male", "female", "neutral"]

    for gender in genders:
        for betas in all_betas:
            generate_taml(betas, gender)
