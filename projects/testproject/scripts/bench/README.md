# Bench scripts — these live on the Acer laptop

Copies of the scripts that run on the robot bench (`gaikwad-prakash@192.168.194.228`),
kept here because they have been rewritten from memory more than once across
sessions. **The Acer holds the working copies in `~/`; these are the record.**

None of them are run from this repo. To use one, copy it to the laptop's home
directory. See `docs/MACHINES.md` for which machine does what.

| file | moves the arm? | purpose |
|---|---|---|
| `arm_ports.py` | no | resolve follower/leader ports BY SERIAL — the `/dev/ttyACM*` numbers move |
| `camfind.py` | no | resolve cameras BY NAME — the `/dev/video*` indices move too |
| `epcount.py` | no | episodes in a dataset, read from its own metadata |
| `probe_ports.py` | no | which serial port has responding motors |
| `startgap.py` | no | leader vs follower pose, normalised through each arm's calibration |
| `notorque.py` | no | 30 s bus hammer on the follower, torque never enabled |
| `notorque_leader.py` | no | the same on the leader — the control |
| `gripcheck.py` | no | per-joint load, voltage, temperature |
| `findgrasp.py` | no | locate the grasp in a recorded episode |
| `safe.py` | **releases torque** | report torque state, then disable. Run after ANY crashed arm program |
| `voltrace.py` | **enables torque** | log supply voltage up to the moment of a USB dropout |
| `synctest.py` | **MOVES THE ARM** | 60 s teleoperation, measures follower tracking error |
| `rec_esp.sh` | **MOVES THE ARM** | record demonstrations |
| `convert_trim_v21.py` | no | v3.0 -> v2.1 conversion with trimming (runs on the Acer, where the recordings are) |
| `plan_convert.py` | no | dry-run of the above — prints the per-episode plan, writes nothing |

## Two rules these encode

**Never address a device by number.** `/dev/ttyACM0` was the leader one morning
and the follower by evening; camera indices have swapped twice. `arm_ports.py`
and `camfind.py` refuse rather than guess.

**Torque survives a crash.** When the USB drops, `disconnect()` never completes,
so the servos stay powered and holding. Run `safe.py` after any crashed run.
