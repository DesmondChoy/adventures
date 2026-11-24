#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC="$ROOT_DIR/formal/AdventureLifecycle.tla"
CLEAN_CFG="$ROOT_DIR/formal/AdventureLifecycle.cfg"

resolve_java() {
  if [[ -n "${JAVA:-}" && -x "${JAVA}" ]]; then
    echo "$JAVA"
    return
  fi
  if command -v java >/dev/null 2>&1 && java -version >/dev/null 2>&1; then
    command -v java
    return
  fi
  local cached_java
  cached_java="$(find "$HOME/.cache" -maxdepth 6 -path '*/bin/java' -type f 2>/dev/null | head -n 1 || true)"
  if [[ -n "$cached_java" && -x "$cached_java" ]]; then
    echo "$cached_java"
    return
  fi
  echo "ERROR: No Java 11+ runtime found. Install Temurin/OpenJDK or set JAVA=/path/to/java." >&2
  exit 2
}

resolve_tla2tools() {
  if [[ -n "${TLA2TOOLS:-}" && -f "${TLA2TOOLS}" ]]; then
    echo "$TLA2TOOLS"
    return
  fi
  local cached_jar
  cached_jar="$(find "$HOME/.cache" -maxdepth 4 -name 'tla2tools*.jar' -type f 2>/dev/null | head -n 1 || true)"
  if [[ -n "$cached_jar" && -f "$cached_jar" ]]; then
    echo "$cached_jar"
    return
  fi
  echo "ERROR: tla2tools.jar not found. Set TLA2TOOLS=/path/to/tla2tools-1.7.4.jar." >&2
  exit 2
}

JAVA_BIN="$(resolve_java)"
TLA_JAR="$(resolve_tla2tools)"
TMP_META="$(mktemp -d)"
trap 'rm -rf "$TMP_META"' EXIT

run_tlc() {
  local cfg="$1"
  local metadir="$TMP_META/$(basename "$cfg" .cfg)"
  "$JAVA_BIN" -XX:+UseParallelGC -cp "$TLA_JAR" tlc2.TLC \
    -workers 1 -fp 0 -lncheck final -metadir "$metadir" \
    -config "$cfg" "$SPEC"
}

echo "1) Verifying clean AdventureLifecycle spec..."
run_tlc "$CLEAN_CFG"

declare -a REPLAYS=(
  "Bug3dfb9bdStaleClientOverwrite.cfg:ServerStateAuthoritative"
  "BugF4b9b11PrematureReveal.cfg:SummaryOnlyAfterConclusion"
  "BugBf68786UnlockedSummaryFallback.cfg:ValidSummaryNeverClobbered"
  "Bug88e1ab5DuplicateInitialRow.cfg:SingleRecordPerAdventure"
  "BugInitialSaveRetainedState.cfg:NoUnsavedChapterProgress"
)

echo "2) Verifying each historical/live bug replay violates its expected invariant..."
for entry in "${REPLAYS[@]}"; do
  cfg_name="${entry%%:*}"
  expected_inv="${entry##*:}"
  cfg_path="$ROOT_DIR/formal/replays/$cfg_name"
  set +e
  output="$(run_tlc "$cfg_path" 2>&1)"
  status=$?
  set -e
  if [[ $status -eq 0 ]]; then
    echo "ERROR: Replay $cfg_name unexpectedly PASSED (expected violation of $expected_inv)!" >&2
    exit 1
  fi
  if ! grep -q "Invariant $expected_inv is violated" <<<"$output"; then
    echo "ERROR: Replay $cfg_name failed, but did not violate $expected_inv:" >&2
    echo "$output" >&2
    exit 1
  fi
  echo "   OK: $cfg_name violated $expected_inv as expected"
done

echo "All TLA+ formal verification checks passed."
