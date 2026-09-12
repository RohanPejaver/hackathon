#!/usr/bin/env bash
# Generate a single self-contained handoff file per role.
# Usage: ./scripts/bundle-docs.sh          (builds all three)
#        ./scripts/bundle-docs.sh core     (builds one)
#
# Prefer sharing the git repo. These bundles are for teammates who can't clone.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p handoff

COMMON="CLAUDE.md docs/CLAUDE.md docs/PROJECT_STATE.md docs/README.md
        docs/product/01-thesis.md docs/product/02-safety-boundaries.md
        docs/engineering/40-team-split.md"

CORE="$COMMON docs/product/03-scenarios.md
      docs/architecture/10-system-overview.md docs/architecture/11-domain-model.md
      docs/architecture/12-event-model.md docs/architecture/13-state-model.md
      docs/architecture/14-contamination-model.md docs/architecture/15-risk-engine.md
      docs/architecture/16-alert-model.md docs/architecture/17-order-model.md
      docs/architecture/18-allergen-knowledge.md docs/architecture/19-temporal-model.md
      docs/architecture/22-interfaces.md docs/architecture/23-failure-modes.md
      docs/engineering/30-repository-layout.md docs/engineering/31-configuration.md
      docs/engineering/33-testing-strategy.md docs/engineering/34-evaluation-framework.md
      docs/engineering/36-replay-and-scenarios.md docs/engineering/38-workflow.md
      docs/engineering/39-implementation-plan.md"

PERCEPTION="$COMMON
      docs/architecture/10-system-overview.md docs/architecture/12-event-model.md
      docs/architecture/19-temporal-model.md docs/architecture/20-spatial-model.md
      docs/architecture/21-perception-contract.md docs/architecture/22-interfaces.md
      docs/architecture/23-failure-modes.md docs/architecture/24-privacy-security.md
      docs/engineering/30-repository-layout.md docs/engineering/31-configuration.md
      docs/engineering/34-evaluation-framework.md docs/engineering/35-data-and-simulation.md
      docs/engineering/38-workflow.md docs/engineering/39-implementation-plan.md"

INTERFACE="$COMMON docs/product/03-scenarios.md
      docs/architecture/10-system-overview.md docs/architecture/16-alert-model.md
      docs/architecture/17-order-model.md docs/architecture/22-interfaces.md
      docs/architecture/25-observability.md docs/architecture/26-human-interaction.md
      docs/engineering/30-repository-layout.md docs/engineering/33-testing-strategy.md
      docs/engineering/37-demo-plan.md docs/engineering/38-workflow.md
      docs/engineering/39-implementation-plan.md"

build () {
  local role="$1"; shift
  local out="handoff/${role}.md"
  {
    echo "# HANDOFF BUNDLE — $(echo "$role" | tr "[:lower:]" "[:upper:]")"
    echo
    echo "Generated $(date '+%Y-%m-%d %H:%M'). Everything below is the project specification."
    echo "Your kickoff prompt is in \`docs/engineering/40-team-split.md\`, included here."
    echo
    echo "**Read order:** PROJECT_STATE -> product/01-thesis -> your architecture docs ->"
    echo "engineering/38-workflow. Do not skip \`docs/CLAUDE.md\` — it governs how you work."
    echo
    local seen=""
    for f in "$@"; do
      case " $seen " in *" $f "*) continue;; esac
      seen="$seen $f"
      [ -f "$f" ] || { echo "MISSING: $f" >&2; continue; }
      echo
      echo '<!-- ==================================================================== -->'
      echo "# FILE: $f"
      echo '<!-- ==================================================================== -->'
      echo
      cat "$f"
      echo
    done
  } > "$out"
  printf '  %-28s %5s lines  %6s\n' "$out" "$(wc -l < "$out" | tr -d ' ')" "$(du -h "$out" | cut -f1)"
}

echo "Bundles written:"
case "${1:-all}" in
  core)       build core       $CORE ;;
  perception) build perception $PERCEPTION ;;
  interface)  build interface  $INTERFACE ;;
  all)        build core $CORE; build perception $PERCEPTION; build interface $INTERFACE ;;
  *) echo "usage: $0 [core|perception|interface|all]" >&2; exit 1 ;;
esac
