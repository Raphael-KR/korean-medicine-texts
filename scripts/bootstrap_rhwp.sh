#!/usr/bin/env bash
set -euo pipefail

RHWP_REPO="${RHWP_REPO:-https://github.com/Raphael-KR/rhwp.git}"
RHWP_DIR="${RHWP_DIR:-vendor/rhwp}"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required" >&2
  exit 1
fi

if ! command -v cargo >/dev/null 2>&1; then
  echo "Rust cargo is required. Install Rust first: https://rustup.rs/" >&2
  exit 1
fi

if [ ! -d "$RHWP_DIR/.git" ]; then
  mkdir -p "$(dirname "$RHWP_DIR")"
  git clone "$RHWP_REPO" "$RHWP_DIR"
else
  git -C "$RHWP_DIR" fetch --all --tags
  git -C "$RHWP_DIR" pull --ff-only
fi

cargo build --release --manifest-path "$RHWP_DIR/Cargo.toml"

echo "rhwp built: $RHWP_DIR/target/release/rhwp"
echo "To use it explicitly:"
echo "  export RHWP_BIN=\"$PWD/$RHWP_DIR/target/release/rhwp\""
