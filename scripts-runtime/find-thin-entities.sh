#!/bin/bash
# Find thin entities in Obsidian vault (< 200 characters)

VAULT_DIR="${VAULT_DIR:-$HOME/alfred/alfred}"

if [[ ! -d "$VAULT_DIR" ]]; then
    echo "Vault not found: $VAULT_DIR"
    exit 1
fi

# Find all .md files, count body content (excluding frontmatter), output if < 200 chars
find "$VAULT_DIR" -name "*.md" -type f ! -path "*/\.*" | while read -r file; do
    # Skip _templates and _archive
    if [[ "$file" == *"/_templates/"* ]] || [[ "$file" == *"/_archive/"* ]]; then
        continue
    fi
    
    # Remove frontmatter and count
    body_size=$(awk '/^---$/{flag=!flag;next}!flag' "$file" | wc -c | xargs)
    
    if [[ $body_size -lt 200 ]]; then
        echo "$file ($body_size chars)"
    fi
done | sort -t'(' -k2 -n
