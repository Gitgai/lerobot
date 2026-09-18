import sys
sys.path.insert(0, "/home/kiran/projects/git/nvidia/lerobot/projects/testproject/configs")
import leisaac_so101_gr00t_config  # registers NEW_EMBODIMENT into MODALITY_CONFIGS
from gr00t.data.embodiment_tags import EmbodimentTag
from gr00t.data.stats import main
main("/home/kiran/lerobot_assets/datasets/new30_plus_recov30", EmbodimentTag.NEW_EMBODIMENT)
print("STATS_DONE")
