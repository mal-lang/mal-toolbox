#!/usr/bin/env bash

set -euo pipefail

cleanup() {
  if [[ "$?" -eq 0 ]]; then
    rm -rf malc_result.zip new_langspec.json langspec.json icons/
  fi
}

trap cleanup EXIT


mal_files=()

langs=(
  "coreLang"
  "enterpriseLang"
  "exampleLang"
  "SCL-Lang"
  "vehicleLang"
  "wiki-example"
  )

mkdir -p langs

for lang in "${langs[@]}"; do
  mal_dir="langs/$lang/src/main/mal"

  if [[ ! -d "$mal_dir" ]]; then
    git clone https://github.com/mal-lang/$lang langs/$lang
  fi

  if [[ -r "$mal_dir/main.mal" ]]; then
    mal_files+=("$mal_dir/main.mal")
  elif [[ -r "$mal_dir/${lang//-}.mal" ]]; then
    mal_files+=("$mal_dir/${lang//-}.mal")
  else
    echo "could not locate entry mal file for $lang"
    exit 1
  fi
done

for file in "${mal_files[@]}"; do
  if [[ "${file#langs/}" =~ ^_.*$ ]]; then
    continue
  fi
  echo "checking file: $file"

  malc -o malc_result.zip "$file"
  unzip -q -o malc_result.zip
  python -m json.tool --indent 2 langspec.json >| langspec.json_
  mv langspec.json_ langspec.json
  ./run.py "$file"
  (python <<HERE
import json
import sys

with open("langspec.json") as f:
  malc = json.load(f)
  for k,v in malc.items():
    if isinstance(v, dict):
      malc[k] = dict(sorted(malc[k].items()))
    elif isinstance(v, list):
      malc[k] = sorted(malc[k], key=lambda i: i["name"])

with open("new_langspec.json") as f:
  new_malc = json.load(f)
  for k,v in new_malc.items():
    if isinstance(v, dict):
      malc[k] = dict(sorted(new_malc[k].items()))
    elif isinstance(v, list):
      new_malc[k] = sorted(new_malc[k], key=lambda i: i["name"])


if malc != new_malc:
  print("compile result differs")
  sys.exit(1)
HERE
) && ec=0 || ec=$?

  if [[ "$ec" -eq 0 ]]; then
    echo "file compiled successfully"
  else
    cat -n langspec.json >| numbered_langspec.json
    cat -n new_langspec.json >| numbered_new_langspec.json
    diff --side-by-side --suppress-common-lines numbered_langspec.json numbered_new_langspec.json | less || :


    echo -e "\nchecked file: $file"

    read -p "Continue? [Y/n] "

    if [[ "$REPLY" == 'n' ]]; then
      exit 1
    fi
  fi
done

