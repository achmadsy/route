#!/usr/bin/env bash
# Classify route task with Jev System One. Exit nonzero when caller must use normal fallback.
set -u

request=${1-}
if [[ -z "$request" ]]; then
  printf '%s\n' 'jev classifier: missing request' >&2
  exit 2
fi

base_url=${ANTHROPIC_BASE_URL-}
if [[ -z "$base_url" ]]; then
  printf '%s\n' 'jev classifier: ANTHROPIC_BASE_URL is not set' >&2
  exit 2
fi

if [[ -n ${ANTHROPIC_AUTH_TOKEN-} ]]; then
  auth_token=$ANTHROPIC_AUTH_TOKEN
elif [[ -n ${ANTHROPIC_API_KEY-} ]]; then
  auth_token=$ANTHROPIC_API_KEY
else
  printf '%s\n' 'jev classifier: no Claude credential configured' >&2
  exit 2
fi

if ! command -v curl >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
  printf '%s\n' 'jev classifier: curl and jq are required' >&2
  exit 2
fi

endpoint=${base_url%/}/systemone
payload=$(jq -n --arg state "$request" '{
  model: "oc/jev-1.13-free",
  state: $state,
  questions: {
    probe: {type: "noul", instructions: "Is this request only asking for research, explanation, codebase discovery, or feasibility analysis with no code changes?"},
    direct: {type: "noul", instructions: "Is this a small, isolated, clear, non-bug code change with an obvious verification path?"},
    debug: {type: "noul", instructions: "Does this request describe a bug, error, failure, crash, regression, or broken behavior that needs root-cause investigation?"},
    architectural: {type: "noul", instructions: "Does this request require architecture, multiple subsystems, public API changes, migrations, security work, or have materially unclear scope?"}
  }
}') || exit 2

response=$(curl --fail --silent --show-error --max-time "${ROUTE_JEV_TIMEOUT_SECONDS:-15}" \
  -H "Authorization: Bearer ${auth_token}" \
  -H 'Content-Type: application/json' \
  -X POST "$endpoint" \
  --data "$payload") || {
  printf '%s\n' 'jev classifier: request failed' >&2
  exit 3
}

if ! jq -e '(.answers | type) == "object"' >/dev/null 2>&1 <<<"$response"; then
  printf '%s\n' 'jev classifier: invalid response' >&2
  exit 3
fi

scores=$(jq -r '
  [.answers.probe.noul, .answers.direct.noul, .answers.debug.noul, .answers.architectural.noul]
  | if any(.[]; type != "number" or . < 0 or . > 1) then error("invalid scores") else . end
  | to_entries
  | sort_by(.value)
  | reverse
  | [.[0].key, .[0].value, .[1].value] | @tsv
' <<<"$response" 2>/dev/null) || {
  printf '%s\n' 'jev classifier: incomplete answers' >&2
  exit 3
}
read -r lane score second_score <<<"$scores"

lanes=(PROBE DIRECT DEBUG ARCHITECTURAL)
selected=${lanes[$lane]-}
if [[ -z "$selected" ]]; then
  printf '%s\n' 'jev classifier: invalid lane' >&2
  exit 3
fi

# Weak or ambiguous scores are not reliable enough to bypass the normal classifier.
if awk "BEGIN { exit !(($score < 0.60) || (($score - $second_score) < 0.15)) }"; then
  printf '%s\n' 'jev classifier: ambiguous scores' >&2
  exit 3
fi

confidence=HIGH
reason="Jev System One classification selected ${selected}."

printf 'CLASSIFIER_STATUS: COMPLETE\nLANE: %s\nCONFIDENCE: %s\nREASON: %s\nCONTEXT_NEEDED: none\n' \
  "$selected" "$confidence" "$reason"
