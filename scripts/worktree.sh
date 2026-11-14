#!/usr/bin/env bash
#
# worktree.sh — per-task git worktree helper for the NetraCare swarm.
# See docs/swarm-workflow.md §4.
#
# Usage:
#   scripts/worktree.sh new   <task-slug> [base-branch]
#   scripts/worktree.sh clean <task-slug>
#   scripts/worktree.sh list
#
# Worktrees land at ../netracare-wt/<slug>. The branch inside the
# worktree is feature/<slug>, created from base-branch (default: the
# current branch at the time of invocation).

set -euo pipefail

cmd="${1:-help}"
slug="${2:-}"
base="${3:-}"

repo_root="$(git rev-parse --show-toplevel)"
wt_root="$(dirname "$repo_root")/netracare-wt"

die() { echo "error: $*" >&2; exit 1; }

case "$cmd" in
  new)
    [ -n "$slug" ] || die "task slug required. usage: $0 new <slug> [base]"
    [[ "$slug" =~ ^[a-z0-9][a-z0-9-]*$ ]] || die "slug must be kebab-case: $slug"
    base="${base:-$(git rev-parse --abbrev-ref HEAD)}"
    mkdir -p "$wt_root"
    target="$wt_root/$slug"
    [ -e "$target" ] && die "worktree already exists at $target"
    git worktree add -b "feature/$slug" "$target" "$base"
    echo
    echo "worktree ready:"
    echo "  path:   $target"
    echo "  branch: feature/$slug (based on $base)"
    echo "  next:   cd $target"
    ;;

  clean)
    [ -n "$slug" ] || die "task slug required. usage: $0 clean <slug>"
    target="$wt_root/$slug"
    [ -d "$target" ] || die "no worktree at $target"
    # Safety: refuse if the worktree has uncommitted changes.
    if [ -n "$(git -C "$target" status --porcelain)" ]; then
      die "worktree $target has uncommitted changes; commit or stash first"
    fi
    branch="$(git -C "$target" rev-parse --abbrev-ref HEAD)"
    git worktree remove "$target"
    git worktree prune
    echo "removed worktree $target"
    echo "branch $branch is still in the repo; delete with:"
    echo "  git branch -d $branch     (merged)"
    echo "  git branch -D $branch     (force)"
    ;;

  list)
    git worktree list
    ;;

  help|-h|--help|"")
    sed -n '2,15p' "$0"
    ;;

  *)
    die "unknown command: $cmd (try: new | clean | list | help)"
    ;;
esac
