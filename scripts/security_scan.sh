#!/usr/bin/env bash
set -euo pipefail

fail=0

# 1) Block sensitive tracked files
while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  base=$(basename "$file")

  if [[ "$base" == ".env" || "$base" == .env.* ]]; then
    if [[ "$base" != ".env.example" ]]; then
      echo "[fail] tracked env file: $file"
      fail=1
    fi
  fi

  if [[ "$file" =~ (^|/)(cache|outputs|jobs_upload|openai_backup)(/|$) ]]; then
    echo "[fail] tracked artifact path: $file"
    fail=1
  fi

  if [[ "$file" =~ (^|/)data/raw(/|$) ]]; then
    echo "[fail] tracked raw data path: $file"
    fail=1
  fi

  if [[ "$file" =~ (embedding|with_embeddings) ]]; then
    if [[ "$file" =~ \.(csv|json|parquet|pkl|npy|npz|db|sqlite|sql|txt|zip|gz|tar)$ ]]; then
      echo "[fail] tracked embedding data: $file"
      fail=1
    fi
  fi

  if [[ "$file" =~ (^|/)data/raw(/|$) ]]; then
    echo "[fail] tracked raw data path: $file"
    fail=1
  fi

done < <(git ls-files)

# 2) Keyword scan (configs/docs + code string literals)
KEYWORD_REGEX='(API_KEY|SECRET|PASSWORD|JWT|NAVER|CLOVA|OPENAI|S3|ACCESS_KEY|CLIENT_SECRET)'
PLACEHOLDER_REGEX='(YOUR_|EXAMPLE|DUMMY|CHANGEME|CHANGE_ME|REPLACE|REDACTED|TBD|TODO|NONE|NULL|\\.\\.\\.|<.*>)'
TEXT_GLOBS=("*.env" "*.env.*" "*.md" "*.yml" "*.yaml" "*.ini" "*.toml" "*.json" "*.txt")
CODE_GLOBS=("*.py")

check_line() {
  local line="$1"
  local content value

  # split file:line:content (content may include colons)
  content="${line#*:*:}"

  if echo "$content" | grep -qiE "os.getenv\\(|getenv\\(|Get-Content|grep \\^REACT_APP_"; then
    return 0
  fi

  if [[ "$content" == *"="* ]]; then
    value="${content#*=}"
  else
    value="${content#*:}"
  fi

  value="$(echo "$value" | tr -d '[:space:]')"

  if [[ -z "$value" || "$value" == '""' || "$value" == "''" ]]; then
    return 0
  fi
  if [[ "$value" == *'${'* ]]; then
    return 0
  fi
  if [[ "$value" == *"..."* || "$value" == *"<"* || "$value" == *">"* ]]; then
    return 0
  fi
  if [[ "$value" =~ ^[A-Z0-9_]+$ ]]; then
    return 0
  fi
  if echo "$value" | grep -qiE "^https?://|\\.ntruss\\.com|\\.amazonaws\\.com"; then
    return 0
  fi
  if echo "$content" | grep -qiE "$PLACEHOLDER_REGEX"; then
    return 0
  fi

  echo "$line"
  return 1
}

text_matches=$(git grep -nI -E "${KEYWORD_REGEX}[A-Z0-9_]*[[:space:]]*[:=][[:space:]]*[^#[:space:]]+" -- "${TEXT_GLOBS[@]}" ':!scripts/security_scan.sh' || true)
if [[ -n "$text_matches" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    if ! check_line "$line"; then
      echo "[fail] possible secret in text/config: $line"
      fail=1
    fi
  done <<< "$text_matches"
fi

code_matches=$(git grep -nI -E "${KEYWORD_REGEX}[A-Z0-9_]*[[:space:]]*=[^#]*['\"][^'\"]+['\"]" -- "${CODE_GLOBS[@]}" ':!scripts/security_scan.sh' || true)
if [[ -n "$code_matches" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    if ! check_line "$line"; then
      echo "[fail] possible secret in code: $line"
      fail=1
    fi
  done <<< "$code_matches"
fi

# 3) Sample data pattern scan
sample_hits=$(grep -RInE "(010-|@|상세주소|위도|경도|좌표|도로명|번지)" ai_modeling/data_samples 2>/dev/null || true)
if [[ -n "$sample_hits" ]]; then
  echo "[fail] sensitive pattern in data_samples:"
  echo "$sample_hits"
  fail=1
fi

if [[ "$fail" -eq 0 ]]; then
  echo "[ok] scan passed"
else
  exit 1
fi
