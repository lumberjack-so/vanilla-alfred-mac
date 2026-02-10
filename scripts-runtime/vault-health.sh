#!/bin/bash
# Vault health check - reports statistics

VAULT_DIR="${VAULT_DIR:-$HOME/alfred/alfred}"

if [[ ! -d "$VAULT_DIR" ]]; then
    echo "Vault not found: $VAULT_DIR"
    exit 1
fi

echo "Vault Health Report"
echo "==================="
echo ""

# Total entities
total=$(find "$VAULT_DIR" -name "*.md" -type f ! -path "*/\.*" ! -path "*/_templates/*" ! -path "*/_archive/*" | wc -l | xargs)
echo "Total entities: $total"

# By category
echo ""
echo "By category:"
for dir in person org proj evt learn doc loc acct asset proc content; do
    if [[ -d "$VAULT_DIR/$dir" ]]; then
        count=$(find "$VAULT_DIR/$dir" -name "*.md" -type f | wc -l | xargs)
        echo "  $dir: $count"
    fi
done

# Thin entities
echo ""
thin=$(bash "$(dirname "$0")/find-thin-entities.sh" 2>/dev/null | wc -l | xargs)
echo "Thin entities (< 200 chars): $thin"

# Archived
archived=$(find "$VAULT_DIR/_archive" -name "*.md" -type f 2>/dev/null | wc -l | xargs)
echo "Archived: $archived"

echo ""
echo "Health: $(if [[ $thin -lt 10 ]]; then echo "GOOD ✓"; else echo "NEEDS ATTENTION ⚠"; fi)"
