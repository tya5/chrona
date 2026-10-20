#!/bin/sh
set -e
cd "$(dirname "$0")"
rm -f plan-*.csv baseline-*.csv plan-*.yaml baseline-*.yaml actual-*.yaml
python3 gen.py
C=../venv/bin/chrona
CAL="standard mon-fri except 2027-03-22 2027-05-03 2027-05-04 2027-05-05"
$C import plan-en.csv -o plan-en.yaml --actual-output actual-en.yaml --project-id programme --title "Programme status" --calendar "$CAL" --as-of 2027-04-14
$C import baseline-en.csv -o baseline-en.yaml --project-id programme --title "Programme status" --calendar "$CAL"
$C import plan-ja.csv -o plan-ja.yaml --actual-output actual-ja.yaml --project-id programme --title "プログラム進捗" --calendar "$CAL" --as-of 2027-04-14
$C import baseline-ja.csv -o baseline-ja.yaml --project-id programme --title "プログラム進捗" --calendar "$CAL"
