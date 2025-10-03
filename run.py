import os
from datetime import datetime

from smpl_sim.smpllib.smpl_local_robot import SMPL_Robot
from smpl_sim.envs.smplenv import SMPLHumanoid
import torch


# ---- Custom betas (10D) ----
# Slightly taller, leaner body
betas = torch.tensor([[0.9, 0.9, 0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
gender = [SMPLHumanoid.GENDER2NUM["male"]]  # 1 = male (0 neutral, 2 female)

# ---- Robot config ----
robot_cfg = {
    "model": "smpl",
    "mesh": False,
    # "sim": "isaacgym",
    "real_weight": True,
    "real_weight_porpotion_capsules": True,
    "real_weight_porpotion_boxes": True,
    # Optional: expose density
    # "geom_params": {"density": {"lb": [1000.0], "ub": [10.0]}},  # ~1000–1200 kg/m^3
}

smpl_robot = SMPL_Robot(robot_cfg)
smpl_robot.load_from_skeleton(betas=betas, gender=gender)

output_folder = "output"

now_str = datetime.now().strftime("%Y-%m-%d|%H:%M:%S")

output_path = os.path.join(output_folder, f"custom_simple2_{now_str}.xml")

# Export to MJCF
smpl_robot.write_xml(output_path)
print(f"Saved humanoid to {output_path}")


# xml_string = smpl_robot.export_xml_string().decode("utf-8")

# with open("custom_humanoid.xml", "w") as f:
#     f.write(xml_string)
