#!/usr/bin/env bash
# R2b: after the orange scored run, the other two single-arm LeIsaac tasks, 50 episodes each, same checkpoint.
R=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/so101_base_sim_test_20261020
until grep -q "SCORED 100 DONE" $R/sim_scored.log 2>/dev/null; do sleep 60; done
until [ -d /home/kiran/sim/leisaac-src/assets/scenes/table_with_cube ] && [ -d /home/kiran/sim/leisaac-src/assets/scenes/lightwheel_toyroom ]; do sleep 60; done
TASK=LeIsaac-SO101-LiftCube-v0      HEADLESS=1 bash $R/run_sim_test.sh 50 liftcube  "Lift the red cube up." 300
TASK=LeIsaac-SO101-CleanToyTable-v0 HEADLESS=1 bash $R/run_sim_test.sh 50 toytable  "Pick two letter e objects into the box, and reset the arm to rest state." 400
echo "=== OTHER TASKS DONE $(date -u +%FT%TZ)" >> $R/sim_scored.log
