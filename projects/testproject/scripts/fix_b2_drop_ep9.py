import warnings

warnings.filterwarnings("ignore")
from lerobot.datasets.dataset_tools import delete_episodes
from lerobot.datasets.lerobot_dataset import LeRobotDataset

b2 = LeRobotDataset(repo_id="local/grasp_b2", root="/data/lerobot_datasets/so101_pick_orange_grasp_b2")
print(f"b2 before: {b2.meta.total_episodes} eps, {b2.num_frames} frames")
out = delete_episodes(
    b2,
    episode_indices=[9],
    repo_id="local/grasp_b2_9ep",
    output_dir="/data/lerobot_datasets/so101_pick_orange_grasp_b2_9ep",
)
print(f"b2_9ep: {out.meta.total_episodes} eps, {out.num_frames} frames -> DONE")
