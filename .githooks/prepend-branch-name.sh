#!/usr/bin/env bash
# Prefix commit messages with the current branch name:
#   feature/photo-resize: <message>
set -euo pipefail

msg_file="$1"
source="${PRE_COMMIT_COMMIT_MSG_SOURCE:-${2:-}}"

# Leave merges, squashes and amends alone
case "$source" in merge|squash|commit) exit 0 ;; esac

branch="$(git symbolic-ref --short -q HEAD || true)"
case "$branch" in ""|develop|master) exit 0 ;; esac

prefix="$branch: "
grep -qF -- "$prefix" <(head -n1 "$msg_file") && exit 0

tmp="$(mktemp)"
{ printf '%s' "$prefix"; cat "$msg_file"; } > "$tmp"
mv "$tmp" "$msg_file"
