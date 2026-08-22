import warnings

warnings.filterwarnings("ignore")
from lerobot.datasets.dataset_tools import merge_datasets
from lerobot.datasets.lerobot_dataset import LeRobotDataset

SRC = {
    "move_cleaned": "/data/lerobot_datasets/so101_pick_orange_move_cleaned",
    "grasp_b1": "/data/lerobot_datasets/so101_pick_orange_grasp_b1",
    "grasp_b2_9ep": "/data/lerobot_datasets/so101_pick_orange_grasp_b2_9ep",
}
dss = [LeRobotDataset(repo_id=f"local/{k}", root=v) for k, v in SRC.items()]
for k, ds in zip(SRC, dss, strict=False):
    print(f"{k}: {ds.meta.total_episodes} eps, {ds.num_frames} frames")
OUT = "/data/lerobot_datasets/so101_orange_49"
m = merge_datasets(dss, output_repo_id="local/so101_orange_49", output_dir=OUT)
print(f"MERGED -> {OUT}: {m.meta.total_episodes} eps, {m.num_frames} frames")
