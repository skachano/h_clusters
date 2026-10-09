#!/usr/bin/env bash
# Phase 0 smoke tests. Run inside the worker container:
#   docker compose run --rm worker smoke/run_smoke.sh
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
out=/data/smoke
mkdir -p "$out"
status=0

run() {  # name, command...
  local name=$1; shift
  local dir=$out/$name
  rm -rf "$dir"; mkdir -p "$dir"; cd "$dir"
  echo "== $name"
  if "$@" > "$name.out" 2> "$name.err"; then echo "   ok"; else echo "   FAILED (see $dir)"; status=1; fi
}

run orca_h2_hf  bash -c "cp $here/h2_hf.inp . && /opt/orca/orca h2_hf.inp"
grep -q "ORCA TERMINATED NORMALLY" $out/orca_h2_hf/orca_h2_hf.out || { echo "   ORCA did not terminate normally"; status=1; }
grep "FINAL SINGLE POINT ENERGY" $out/orca_h2_hf/orca_h2_hf.out || true

run xtb_h2      bash -c "cp $here/h2.xyz . && xtb h2.xyz --gfn 2 --opt"
grep -a -E "TOTAL ENERGY" $out/xtb_h2/xtb_h2.out | tail -1 || true

# GOAT-EXPLORE: plain GOAT keeps H-atom fragments fixed and cannot change shape.
run goat_h3p    bash -c "cp $here/h3p_goat.inp . && /opt/orca/orca h3p_goat.inp"
grep -q "ORCA TERMINATED NORMALLY" $out/goat_h3p/goat_h3p.out || { echo "   GOAT did not terminate normally"; status=1; }
[ -f $out/goat_h3p/h3p_goat.globalminimum.xyz ] && cat $out/goat_h3p/h3p_goat.globalminimum.xyz

exit $status
