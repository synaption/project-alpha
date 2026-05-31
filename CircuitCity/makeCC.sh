#!/usr/bin/env bash
# makeCC.sh — build CircuitCity release binaries.
#
# Usage:  ./makeCC.sh [linux|windows|all]
#         Default: all
#
# Outputs land in dist/ relative to this script.

set -euo pipefail

CARGO="${HOME}/.cargo/bin/cargo"
RUSTUP="${HOME}/.cargo/bin/rustup"
BIN="circuit-cities"
PROJ="$(cd "$(dirname "$0")" && pwd)"
DIST="${PROJ}/dist"

# ---- Colour helpers -------------------------------------------------------

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
step()  { echo -e "\n${BOLD}==> $*${NC}"; }
ok()    { echo -e "    ${GREEN}✓${NC}  $*"; }
warn()  { echo -e "    ${YELLOW}!${NC}  $*"; }
die()   { echo -e "    ${RED}✗${NC}  $*" >&2; exit 1; }

# ---- Argument parsing -----------------------------------------------------

WANT_LINUX=1
WANT_WINDOWS=1

case "${1:-all}" in
  linux)   WANT_WINDOWS=0 ;;
  windows) WANT_LINUX=0   ;;
  all)     ;;
  -h|--help)
    echo "Usage: $0 [linux|windows|all]"
    exit 0 ;;
  *)
    die "Unknown target '$1'.  Use: linux | windows | all" ;;
esac

# ---- Prep -----------------------------------------------------------------

mkdir -p "$DIST"
cd "$PROJ"

echo -e "\n${BOLD}CircuitCity — release build${NC}"

# ---- Linux x86_64 ---------------------------------------------------------

if [[ $WANT_LINUX -eq 1 ]]; then
  step "Linux x86_64"
  "$CARGO" build --release
  cp "target/release/$BIN" "$DIST/${BIN}-linux-x86_64"
  ok "$DIST/${BIN}-linux-x86_64  ($(du -h "target/release/$BIN" | cut -f1))"
fi

# ---- Windows x86_64 (MinGW cross) -----------------------------------------

if [[ $WANT_WINDOWS -eq 1 ]]; then
  step "Windows x86_64  (x86_64-pc-windows-gnu)"

  MISSING=()
  if ! "$RUSTUP" target list --installed 2>/dev/null | grep -q "x86_64-pc-windows-gnu"; then
    MISSING+=("Rust target missing  →  rustup target add x86_64-pc-windows-gnu")
  fi
  if ! command -v x86_64-w64-mingw32-gcc &>/dev/null; then
    MISSING+=("MinGW linker missing →  sudo apt install gcc-mingw-w64-x86-64")
  fi

  if [[ ${#MISSING[@]} -gt 0 ]]; then
    warn "Skipping — prerequisites not met:"
    for m in "${MISSING[@]}"; do echo "      $m"; done
  else
    "$CARGO" build --release --target x86_64-pc-windows-gnu
    cp "target/x86_64-pc-windows-gnu/release/${BIN}.exe" \
       "$DIST/${BIN}-windows-x86_64.exe"
    ok "$DIST/${BIN}-windows-x86_64.exe  ($(du -h "target/x86_64-pc-windows-gnu/release/${BIN}.exe" | cut -f1))"
  fi
fi

# ---- Summary --------------------------------------------------------------

echo ""
echo -e "${BOLD}Artifacts in dist/${NC}:"
ls -lh "$DIST/" 2>/dev/null || echo "  (nothing built)"
echo ""
