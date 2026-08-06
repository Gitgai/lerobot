"""GR00T modality config for LeIsaac SO-101 PickOrange (NEW_EMBODIMENT).

Needed in TWO places:
  1. generating meta/relative_stats.json  (gr00t.data.stats needs the action
     config to know which modalities are relative)
  2. fine-tuning                          (launch_finetune.py --modality-config-path)

Derived from Isaac-GR00T's examples/SO100/so100_config.py, which matches our
data exactly - the LightwheelAI/leisaac-pick-orange dataset has
observation.state and action of shape [6] ordered
    shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper
so single_arm is 0:5 and gripper is 5:6, with video keys front and wrist.

THE ACTION REPRESENTATION IS NOT COSMETIC:
    single_arm -> RELATIVE
    gripper    -> ABSOLUTE
This is the same pair the working 12e21/gr00t_n1d6_leisaac_pick_orange
checkpoint declares in its conf.yaml, so training with anything else would
produce a model that disagrees with the serving path we have already verified.

NOTE the composition happens SERVER-SIDE at inference: the GR00T server applies
to_absolute_chunking() before replying, so a client must NOT add the current
state again. We proved that by probing the wire (see
scripts/gr00t_n17_client_adapter.py) and LeIsaac's native n1.6 client agrees -
it composes nothing.
"""

from gr00t.configs.data.embodiment_configs import register_modality_config
from gr00t.data.embodiment_tags import EmbodimentTag
from gr00t.data.types import (
    ActionConfig,
    ActionFormat,
    ActionRepresentation,
    ActionType,
    ModalityConfig,
)

leisaac_so101_config = {
    "video": ModalityConfig(
        delta_indices=[0],
        modality_keys=["front", "wrist"],
    ),
    "state": ModalityConfig(
        delta_indices=[0],
        modality_keys=["single_arm", "gripper"],
    ),
    "action": ModalityConfig(
        # 16-step action chunk, matching the checkpoint we serve.
        delta_indices=list(range(16)),
        modality_keys=["single_arm", "gripper"],
        action_configs=[
            ActionConfig(
                rep=ActionRepresentation.RELATIVE,
                type=ActionType.NON_EEF,
                format=ActionFormat.DEFAULT,
            ),
            ActionConfig(
                rep=ActionRepresentation.ABSOLUTE,
                type=ActionType.NON_EEF,
                format=ActionFormat.DEFAULT,
            ),
        ],
    ),
    "language": ModalityConfig(
        delta_indices=[0],
        modality_keys=["annotation.human.task_description"],
    ),
}

register_modality_config(leisaac_so101_config, embodiment_tag=EmbodimentTag.NEW_EMBODIMENT)
