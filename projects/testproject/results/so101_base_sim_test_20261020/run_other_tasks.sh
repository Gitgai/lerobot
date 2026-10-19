#!/usr/bin/env bash
# R2b: the other two single-arm LeIsaac tasks. Caps sized to the task (a lift takes seconds; the 100 s cap cost 16 min
# per failed episode): cube 30 s (1,800 steps), toy-table 60 s (3,600 steps).
R=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/so101_base_sim_test_20261020
TASK=LeIsaac-SO101-LiftCube-v0      EP_LEN=30 HEADLESS=1 bash $R/run_sim_test.sh 50 liftcube  "Lift the red cube up." 300
TASK=LeIsaac-SO101-CleanToyTable-v0 EP_LEN=60 HEADLESS=1 bash $R/run_sim_test.sh 40 toytable  "Pick two letter e objects into the box, and reset the arm to rest state." 400
echo "=== OTHER TASKS DONE $(date -u +%FT%TZ)" >> $R/sim_scored.log
