#!/usr/bin/env bash
# Bootstraps the GitHub project structure for the ITS platform:
#   labels -> milestones (M0-M6) -> task issues (50) -> epic issues (14 with
#   task checklists) -> native sub-issue links (task under epic).
#
# Source of truth: scripts/issues.manifest.json
# Rich bodies:     docs/issues/<KEY>.md (tasks), docs/issues/epics/<EKEY>.md (epics)
#
# IDEMPOTENT: skips labels/milestones/issues that already exist and ignores
# already-linked sub-issues, so a partial run can be safely re-run.
#
# Requires: gh (authenticated, 'repo' scope) and jq.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST="$SCRIPT_DIR/issues.manifest.json"
ISSUES_DIR="$REPO_ROOT/docs/issues"
REPO="$(jq -r '.repo' "$MANIFEST")"

command -v gh >/dev/null || { echo "gh CLI required"; exit 1; }
command -v jq >/dev/null || { echo "jq required"; exit 1; }
echo "Repo: $REPO"

# ---- 1. Labels ----
echo "== Labels =="
jq -c '.labels[]' "$MANIFEST" | while read -r l; do
  name=$(jq -r '.name' <<<"$l"); color=$(jq -r '.color' <<<"$l"); desc=$(jq -r '.description' <<<"$l")
  gh label create "$name" -R "$REPO" --color "$color" --description "$desc" --force >/dev/null 2>&1 || true
  echo "  label: $name"
done

# ---- 2. Milestones ----
echo "== Milestones =="
existing_ms="$(gh api "repos/$REPO/milestones?state=all&per_page=100" --jq '.[].title' 2>/dev/null || true)"
jq -c '.milestones[]' "$MANIFEST" | while read -r ms; do
  title=$(jq -r '.title' <<<"$ms"); desc=$(jq -r '.description' <<<"$ms")
  if grep -Fxq "$title" <<<"$existing_ms"; then echo "  exists: $title";
  else gh api "repos/$REPO/milestones" -f title="$title" -f description="$desc" >/dev/null 2>&1 || true; echo "  created: $title"; fi
done

# ---- helper: title -> number / id ----
issue_field() { # $1=title $2=field(number|id)
  gh issue list -R "$REPO" --state all --limit 1000 --json number,title,id \
    --jq ".[] | select(.title==\"$1\") | .$2" | head -n1
}

create_issue() { # $1=title $2=labels(csv) $3=milestone $4=bodyfile
  if [ -n "$(issue_field "$1" number)" ]; then echo "  exists: $1"; return; fi
  local args=(issue create -R "$REPO" --title "$1" --label "$2" --milestone "$3")
  if [ -n "$4" ] && [ -f "$4" ]; then args+=(--body-file "$4");
  else args+=(--body "Detailspezifikation siehe docs/. Siehe docs/01-github-issues.md."); fi
  gh "${args[@]}" >/dev/null
  echo "  created: $1"
}

# ---- 3. Task issues ----
echo "== Task issues =="
jq -c '.tasks[]' "$MANIFEST" | while read -r t; do
  key=$(jq -r '.key' <<<"$t"); title=$(jq -r '.title' <<<"$t")
  labels=$(jq -r '.labels | join(",")' <<<"$t"); ms=$(jq -r '.milestone' <<<"$t")
  create_issue "$title" "$labels" "$ms" "$ISSUES_DIR/$key.md"
done

# ---- 4. Epic issues (with task checklist) ----
echo "== Epic issues =="
jq -c '.epics[]' "$MANIFEST" | while read -r e; do
  key=$(jq -r '.key' <<<"$e"); title=$(jq -r '.title' <<<"$e")
  labels=$(jq -r '.labels | join(",")' <<<"$e"); ms=$(jq -r '.milestone' <<<"$e"); doc=$(jq -r '.doc' <<<"$e")
  if [ -n "$(issue_field "$title" number)" ]; then echo "  exists: $title"; continue; fi
  tmp="$(mktemp)"
  ef="$ISSUES_DIR/epics/$key.md"
  if [ -f "$ef" ]; then cat "$ef" > "$tmp"; else printf '# %s\n\nSiehe %s. Milestone: %s.\n' "$title" "$doc" "$ms" > "$tmp"; fi
  printf '\n\n## Tasks (Sub-Issues)\n' >> "$tmp"
  jq -c --arg ek "$key" '.tasks[] | select(.epic==$ek)' "$MANIFEST" | while read -r t; do
    tkey=$(jq -r '.key' <<<"$t"); ttitle=$(jq -r '.title' <<<"$t")
    num="$(issue_field "$ttitle" number)"
    if [ -n "$num" ]; then printf -- '- [ ] #%s — %s\n' "$num" "$tkey" >> "$tmp";
    else printf -- '- [ ] %s — %s\n' "$tkey" "$ttitle" >> "$tmp"; fi
  done
  gh issue create -R "$REPO" --title "$title" --label "$labels" --milestone "$ms" --body-file "$tmp" >/dev/null
  echo "  created epic: $title"
  rm -f "$tmp"
done

# ---- 5. Native sub-issue links ----
echo "== Sub-issue links =="
Q='mutation($e:ID!,$s:ID!){addSubIssue(input:{issueId:$e,subIssueId:$s}){subIssue{number}}}'
jq -c '.epics[]' "$MANIFEST" | while read -r e; do
  key=$(jq -r '.key' <<<"$e"); title=$(jq -r '.title' <<<"$e")
  epic_id="$(issue_field "$title" id)"; [ -z "$epic_id" ] && continue
  jq -c --arg ek "$key" '.tasks[] | select(.epic==$ek)' "$MANIFEST" | while read -r t; do
    tkey=$(jq -r '.key' <<<"$t"); ttitle=$(jq -r '.title' <<<"$t")
    task_id="$(issue_field "$ttitle" id)"; [ -z "$task_id" ] && continue
    if gh api graphql -H "GraphQL-Features: sub_issues" -f query="$Q" -f e="$epic_id" -f s="$task_id" >/dev/null 2>&1; then
      echo "  linked: $tkey -> $key"
    else
      echo "  skip (already linked / unsupported): $tkey -> $key"
    fi
  done
done
echo "Bootstrap complete."
