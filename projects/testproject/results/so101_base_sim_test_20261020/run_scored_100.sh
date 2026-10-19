#!/usr/bin/env bash
# R2 scored run: 50 episodes with the corpus's own instruction, then 50 with ours; headless; seeds 100.. and 200..
R=/home/kiran/projects/git/nvidia/lerobot/projects/testproject/results/so101_base_sim_test_20261020
HEADLESS=1 bash $R/run_sim_test.sh 50 corpusA "Grab oranges and place into plate." 100
HEADLESS=1 bash $R/run_sim_test.sh 50 oursB "pick up the orange and move it to another place" 200
echo "=== SCORED 100 DONE $(date -u +%FT%TZ)" >> $R/sim_scored.log
