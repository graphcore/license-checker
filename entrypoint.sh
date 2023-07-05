#!/bin/bash

arg_prefix="--"

flags_supplied=()

while [[ $# -gt 0 ]]; do
  if [[ "$1" == "$arg_prefix"* ]]; then
    raw_var_name="${1#$arg_prefix}"
    var_name=$(echo "$raw_var_name" | sed 's/[^A-Za-z0-9_]/_/g')
    flags_supplied+=($raw_var_name)
    shift
  else
    prev_var_name="${var_name}"
    declare "${prev_var_name}+=${1} "
    shift
  fi
done

# Defaults
if ! [[ "${flags_supplied[@]}" =~ "repository" ]]; then
  repository=/usr/src/source_repo
  flags_supplied+=("repository")
fi

if ! [[ "${flags_supplied[@]}" =~ "output-path" ]]; then
  output_path=/usr/src/output/license-output.html
  flags_supplied+=("output-path")
fi

# Build the output command
output_command="python3 -m gc_licensing"

for f in "${flags_supplied[@]}"; do
  var_name=$(echo "$f" | sed 's/[^A-Za-z0-9_]/_/g')
  output_command+=" --$f ${!var_name}"
done

# Run it
$output_command
