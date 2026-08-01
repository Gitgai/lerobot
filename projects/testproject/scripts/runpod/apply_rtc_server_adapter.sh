#!/usr/bin/env bash
# Add the RTC (Real-Time Chunking) adapter to the POD's policy_server (training-era code).
# The old code already ships the full RTC module + Pi05 integration; this adapter is the
# only missing piece: it feeds inference_delay + prev_chunk_left_over into the policy and
# enables RTC via env vars at load time. RTC stays OFF unless RTC_ENABLE=1 is set when
# starting the server - without it, behavior is byte-identical.
#
# Run FROM THE LAPTOP repo root:
#   bash projects/testproject/scripts/runpod/apply_rtc_server_adapter.sh <POD_IP> <POD_PORT>
# Idempotent; makes policy_server.py.rtc.bak once; fails loudly if anchors are missing.
set -euo pipefail

POD_IP="${1:?pod ip}"
POD_PORT="${2:?pod ssh port}"
KEY="$HOME/.ssh/runpod_ed25519"
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o BatchMode=yes"
TARGET=/workspace/lerobot/src/lerobot/async_inference/policy_server.py

ssh $SSH_OPTS -p "$POD_PORT" -i "$KEY" "root@$POD_IP" "python3 - <<'PYEOF'
from pathlib import Path

p = Path('$TARGET')
src = p.read_text()
if '_init_rtc_from_env' in src:
    print('RTC adapter already applied')
    raise SystemExit(0)

def sub_once(anchor, replacement):
    global src
    assert src.count(anchor) == 1, 'anchor not found or ambiguous: ' + anchor[:60]
    src = src.replace(anchor, replacement, 1)

Path(str(p) + '.rtc.bak').write_text(src)

# 1. imports
sub_once('import pickle  # nosec\n',
         'import math\nimport os\nimport pickle  # nosec\n')

# 2. reset RTC state when a new client connects
sub_once('''        with self._predicted_timesteps_lock:
            self._predicted_timesteps = set()

    def Ready(self, request, context):''',
         '''        with self._predicted_timesteps_lock:
            self._predicted_timesteps = set()
        self._rtc_prev_chunk = None
        self._rtc_prev_i0 = None

    def Ready(self, request, context):''')

# 3. enable RTC (env-gated) right after the policy is loaded
sub_once('''        self.policy = policy_class.from_pretrained(policy_specs.pretrained_name_or_path)
        self.policy.to(self.device)''',
         '''        self.policy = policy_class.from_pretrained(policy_specs.pretrained_name_or_path)
        self.policy.to(self.device)
        self._init_rtc_from_env()''')

# 4. adapter methods
sub_once('    def _time_action_chunk(self, t_0: float,',
         '''    def _init_rtc_from_env(self):
        \"\"\"Enable Real-Time Chunking when RTC_ENABLE=1. No effect otherwise.\"\"\"
        self._rtc_on = False
        self._rtc_prev_chunk = None
        self._rtc_prev_i0 = None
        if os.environ.get(\"RTC_ENABLE\") != \"1\":
            return
        from lerobot.policies.rtc.configuration_rtc import RTCConfig

        horizon = int(os.environ.get(\"RTC_EXEC_HORIZON\", \"10\"))
        self.policy.config.rtc_config = RTCConfig(enabled=True, execution_horizon=horizon)
        self.policy.init_rtc_processor()
        self.policy.model.rtc_processor = self.policy.rtc_processor
        self._rtc_last_latency_s = float(os.environ.get(\"RTC_INIT_LATENCY_S\", \"0.8\"))
        self._rtc_margin_s = float(os.environ.get(\"RTC_DELAY_MARGIN_S\", \"0.25\"))
        self._rtc_on = True
        self.logger.info(f\"RTC enabled (execution_horizon={horizon})\")

    def _rtc_inference_kwargs(self, observation_t):
        \"\"\"Build inference_delay + prev_chunk_left_over (normalized space) for RTC.\"\"\"
        if not getattr(self, \"_rtc_on\", False):
            return {}
        delay = math.ceil((self._rtc_last_latency_s + self._rtc_margin_s) / self.config.environment_dt)
        prev = None
        if self._rtc_prev_chunk is not None and self._rtc_prev_i0 is not None:
            offset = observation_t.get_timestep() - self._rtc_prev_i0
            if 0 <= offset < self._rtc_prev_chunk.shape[1]:
                prev = self._rtc_prev_chunk[:, offset:, :]
        return {\"inference_delay\": delay, \"prev_chunk_left_over\": prev}

    def _time_action_chunk(self, t_0: float,''')

# 5. pass kwargs through _get_action_chunk
sub_once('''    def _get_action_chunk(self, observation: dict[str, torch.Tensor]) -> torch.Tensor:
        \"\"\"Get an action chunk from the policy. The chunk contains only\"\"\"
        chunk = self.policy.predict_action_chunk(observation)''',
         '''    def _get_action_chunk(self, observation: dict[str, torch.Tensor], **rtc_kwargs) -> torch.Tensor:
        \"\"\"Get an action chunk from the policy. The chunk contains only\"\"\"
        chunk = self.policy.predict_action_chunk(observation, **rtc_kwargs)''')

# 6. wire RTC into the inference call + remember the (normalized) chunk
sub_once('''        start_inference = time.perf_counter()
        action_tensor = self._get_action_chunk(observation)
        inference_time = time.perf_counter() - start_inference''',
         '''        start_inference = time.perf_counter()
        rtc_kwargs = self._rtc_inference_kwargs(observation_t)
        action_tensor = self._get_action_chunk(observation, **rtc_kwargs)
        inference_time = time.perf_counter() - start_inference
        if getattr(self, \"_rtc_on\", False):
            self._rtc_prev_chunk = action_tensor.detach().clone()
            self._rtc_prev_i0 = observation_t.get_timestep()
            self._rtc_last_latency_s = inference_time''')

p.write_text(src)
import py_compile
py_compile.compile(str(p), doraise=True)
print('RTC adapter applied and compiled OK (backup: policy_server.py.rtc.bak)')
PYEOF"
