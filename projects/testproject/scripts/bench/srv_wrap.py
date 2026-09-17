import signal, sys, runpy
# Something on this box kills the GR00T server with signal 16 (SIGSTKFLT),
# intermittently. Signal 16 is catchable (unlike SIGKILL/SIGSTOP). If we ignore
# it, the server survives whatever is sending it. Log if it arrives.
try:
    signal.signal(signal.SIGSTKFLT, signal.SIG_IGN)
    print("[wrap] ignoring SIGSTKFLT(16)", flush=True)
except Exception as e:
    print("[wrap] could not set SIGSTKFLT handler:", e, flush=True)
# also guard a couple of other odd signals just in case
for s in ("SIGUSR1","SIGUSR2"):
    try: signal.signal(getattr(signal,s), signal.SIG_IGN)
    except Exception: pass
sys.argv = [
    "run_gr00t_server.py",
    "--model-path","/home/kiran/lerobot_assets/checkpoints/n16_new30_v1/n16_new30_v1/checkpoint-6000",
    "--embodiment-tag","NEW_EMBODIMENT",
    "--modality-config-path","/home/kiran/projects/git/nvidia/lerobot/projects/testproject/configs/leisaac_so101_gr00t_config.py",
    "--host","0.0.0.0","--port","5555",
]
runpy.run_path("/home/kiran/sim/Isaac-GR00T-n16/gr00t/eval/run_gr00t_server.py", run_name="__main__")
