# Alfred KB - Knowledge Management

**Purpose:** Manage the Obsidian vault as Alfred's knowledge base.

## Vault Structure

```
alfred/
├── person/     # People (contacts, relationships)
├── org/        # Organizations (companies, institutions)
├── proj/       # Projects (work initiatives)
├── evt/        # Events (meetings, milestones)
├── learn/      # Learning resources (articles, courses)
├── doc/        # Documents (notes, references)
├── loc/        # Locations (addresses, places)
├── acct/       # Accounts (services, credentials)
├── asset/      # Assets (equipment, resources)
├── proc/       # Procedures (workflows, processes)
├── content/    # Content (published work)
├── _archive/   # Archived entities
└── _templates/ # Entity templates
```

## Entity Management

### Creating Entities

```bash
# Create a person
cat > ~/alfred/alfred/person/john-doe.md <<EOF
---
type: person
name: John Doe
email: john@example.com
tags: [contact, work]
---

# John Doe

## Context
Brief description of who they are and your relationship.

## Notes
- Met at conference 2024
- Working on Project X together
EOF
```

### Searching

```bash
# Find entities by name
grep -r "John Doe" ~/alfred/alfred/

# Find by tag
grep -r "tags: .*work" ~/alfred/alfred/
```

## Wikilinks

Use `[[entity-name]]` to link between entities:
- `[[john-doe]]` - Person
- `[[acme-corp]]` - Organization  
- `[[project-alpha]]` - Project

## Frontmatter Fields

Required for all entities:
```yaml
---
type: person|org|proj|evt|learn|doc|loc|acct|asset|proc|content
name: Display Name
created: YYYY-MM-DD
tags: [tag1, tag2]
---
```

Optional:
```yaml
status: active|paused|completed|archived
related: [entity-1, entity-2]
description: Brief one-liner
```

## Commands

**Read entity:**
```python
with open(f"{vault_path}/{category}/{slug}.md") as f:
    content = f.read()
```

**Update entity:**
```python
# Append to entity
with open(f"{vault_path}/person/john-doe.md", "a") as f:
    f.write("\n## 2024-02-10 Meeting Notes\n...")
```

**Search:**
```bash
# Full-text search
find ~/alfred/alfred -name "*.md" -exec grep -l "search term" {} \;
```

## Best Practices

1. **One entity per file** - Don't merge multiple people/projects
2. **Use slugs** - Filenames: `lowercase-with-dashes.md`
3. **Frontmatter first** - Always start with YAML frontmatter
4. **Wikilinks everywhere** - Connect related entities
5. **Update, don't replace** - Append new info, preserve history
6. **Archive, don't delete** - Move to `_archive/` instead

## Integration

- **Twenty CRM:** Sync people/orgs to CRM
- **Plane PM:** Sync projects to Plane issues
- **Calendar:** Link events to vault entries
- **Email:** Extract entities from conversations

## Maintenance Scripts

```bash
# Find thin entities (< 200 chars)
~/clawd/scripts/find-thin-entities.sh

# Check vault health
~/clawd/scripts/vault-health.sh

# Sync to services
~/clawd/scripts/vault-sync.sh
```

## Obsidian Plugins (Recommended)

Install these in Obsidian:
- **Dataview** - Query entities
- **Templater** - Entity templates
- **Calendar** - Event management
- **Excalidraw** - Diagrams

## CLI Access

```bash
# Obsidian CLI (if installed)
obsidian-cli search "term"
obsidian-cli create person/new-person.md
```
