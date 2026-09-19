import signal, sys, runpy, os
# Same SIGSTKFLT(16) guard as srv_wrap.py (something on this box sends it).
try:
    signal.signal(signal.SIGSTKFLT, signal.SIG_IGN)
    print("[wrap] ignoring SIGSTKFLT(16)", flush=True)
except Exception as e:
    print("[wrap] could not set SIGSTKFLT handler:", e, flush=True)
for s in ("SIGUSR1","SIGUSR2"):
    try: signal.signal(getattr(signal,s), signal.SIG_IGN)
    except Exception: pass
CK = os.environ.get("RECOV_CKPT", "6000")   # 3000 or 6000
MODEL = f"/home/kiran/lerobot_assets/checkpoints/n16_recovery_v1/n16_recovery_v1/checkpoint-{CK}"
print(f"[wrap] serving recovery checkpoint-{CK}: {MODEL}", flush=True)
sys.argv = [
    "run_gr00t_server.py",
    "--model-path", MODEL,
    "--embodiment-tag","NEW_EMBODIMENT",
    "--modality-config-path","/home/kiran/projects/git/nvidia/lerobot/projects/testproject/configs/leisaac_so101_gr00t_config.py",
    "--host","0.0.0.0","--port","5555",
]
runpy.run_path("/home/kiran/sim/Isaac-GR00T-n16/gr00t/eval/run_gr00t_server.py", run_name="__main__")
