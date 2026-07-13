import warnings; warnings.filterwarnings("ignore")
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.datasets.dataset_tools import merge_datasets

SRC = {
    "move_cleaned": "/data/lerobot_datasets/so101_pick_orange_move_cleaned",
    "grasp_b1":     "/data/lerobot_datasets/so101_pick_orange_grasp_b1",
    "grasp_b2":     "/data/lerobot_datasets/so101_pick_orange_grasp_b2",
}
dss = []
for k, root in SRC.items():
    ds = LeRobotDataset(repo_id=f"local/{k}", root=root)
    print(f"{k}: {ds.meta.total_episodes} eps, {ds.num_frames} frames, cams={ds.meta.camera_keys}")
    dss.append(ds)

OUT = "/data/lerobot_datasets/so101_orange_50"
merged = merge_datasets(dss, output_repo_id="local/so101_orange_50", output_dir=OUT)
print(f"MERGED -> {OUT}: {merged.meta.total_episodes} eps, {merged.num_frames} frames")
