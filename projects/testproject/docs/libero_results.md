# LIBERO Results

Policy:

```text
lerobot/pi05_libero_finetuned
```

Simulator:

```text
LIBERO
```

## Completed Results

| Suite | Tasks | Episodes | Success |
| --- | --- | ---: | ---: |
| LIBERO Object | 0-9 | 100 | 99% |
| LIBERO Spatial | 0-9 | 100 | 97% |
| LIBERO Goal | 0-9 | 100 | 96% |

## Local Video Folders

```text
/data/downloads/pi05_libero_object_tasks_0to9_10eps/
/data/downloads/pi05_libero_spatial_tasks_0to9_10eps/
/data/downloads/pi05_libero_goal_tasks_0to9_10eps/
```

Open a folder:

```bash
xdg-open /data/downloads/pi05_libero_goal_tasks_0to9_10eps
```

## LIBERO 10

Attempted twice:

```text
Suite: libero_10
Tasks: 0-9
Episodes: 10 per task
Policy: lerobot/pi05_libero_finetuned
```

Result:

```text
The Brev L4 instance became UNHEALTHY during startup/loading.
SSH timed out.
The run did not complete.
```

Recommendation:

Run `LIBERO 10` on a larger VM instead of retrying repeatedly on the same 16 GB instance.

