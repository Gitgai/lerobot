# Fruit OpenPI client — repository migration candidate

Copied 24 October 2026. This is the fruit 4k synchronous integration, not the older LeRobot RTC client. RTC off, network JPEG off, 30 action rows, original project timing guard unchanged. No new limits, motor settings or policy changes.

**Do not treat this migration as approval/readiness for a physical trial.** The Acer NVMe problem remains unresolved. Existing operational scripts were not replaced. Default client execution accesses real cameras/motors even without `--execute`; only `--help`, imports, compilation and the pure tests below are hardware-free.

## Files and provenance

- Seven files (`client.py`, `transport.py`, `server.py`, `contract.py`, `freshness.py`, `test_contract.py`, `test_freshness.py`) came from `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/fruit_openpi_client/`.
- `frame_recorder.py` came from that workspace's `jpeg_trial_20260930/`.
- `so101_trial_safety.py` came from `/home/gaikwad-prakash/so101_trial_safety.py`, including historical helper functions not used by this client. No new home checks or movement behavior were added.
- Migration edits: client uses co-located helpers and the original network Python by absolute path; transport uses the original pinned codec by absolute path. Repository hooks subsequently formatted all nine files, sorted/cleaned imports and applied equivalent literal/loop-variable cleanups. The copies are no longer byte-identical. See `MIGRATION_HASHES.json` for original and final SHA-256 values. Original files are untouched.

## Dependencies intentionally not moved

- Robot Python: `/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv/bin/python`.
- Network Python: `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/openpi_split_validation_20261015/venv/bin/python`.
- Pinned codec: `/home/gaikwad-prakash/Documents/ChatGPT/Lerobot/openpi_split_validation_20261015/vendor`.
- AI90 server uses its existing OpenPI environment and `/home/kiran/sim/openpi-fruit-prep-20261020-0tn2mX` loader/checkpoint. It was not redeployed or started.

The old workspace must remain in place. Do not delete it after copying these files. Network/environment dependency packaging is a later explicit step, not complete here.

## Hardware-free verification

From the repository root:

```bash
/home/gaikwad-prakash/PrakashProjects/lerobot/lerobot/.venv/bin/python -m unittest discover -s projects/testproject/scripts/inference/fruit_openpi -p 'test_*.py'
```

These are contract/timing tests, not a simulated arm or proof of physical safety. Do not run the server as an import check: its top-level code imports the GPU training environment. No full network or real-device integration is established by this migration.

## Evidence remains outside code

Eleven selected documentation snapshots are now under `docs/fruit_openpi_history/`; see its README. Trial images/logs, dataset review assets and checkpoints were not copied here. The original workspace remains intact, including external evidence links and environment dependencies. Documentation snapshots are historical, not live runtime status.

## Rollback

Original files and launch paths are untouched. Continue using the original paths only after the separate runtime readiness checks; do not automatically switch back into a physical trial. Changes here are a separate candidate and require no environment rollback.
