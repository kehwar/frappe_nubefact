---
name: kehwar-skills
description: Expert guidance for managing the kehwar skills repository including agent workflows, sync commands, and skills installation procedures. Use when working with the skills repository, adding/updating skills, syncing between home directory and repository, or troubleshooting skill management issues in fresh agent environments.
license: MIT
---

# kehwar Skills Repository Management

Expert guidance for managing skills in the kehwar skills repository using the skills CLI with proper sync workflows.

## Repository Overview

Personal collection of skills for AI coding agents, managed via the [skills CLI](https://github.com/vercel-labs/skills). Uses official `.skill-lock.json` format and syncs skills between home directory (`~/.agents/`) and repository for version control.

## Critical Agent Workflow

⚠️ **Fresh agent environments start with empty `~/.agents/` directory**

### First-Time Checklist

1. Check if `~/.agents/.skill-lock.json` exists
2. If missing: Run `pnpm sync-to-home` to restore from repository
3. When adding/updating skills: Use `-g` flag (REQUIRED)
4. After any skill changes: Run `pnpm sync-from-home` to sync back

### Why This Matters

- Agents start fresh (no `~/.agents/` folder)
- `-g` flag ensures skills install to `~/.agents/` where lockfile tracks them
- Without `-g`: skills install to project-local `.agents/`, lockfile won't update
- Sync-to-home restores existing skills for proper management

## Skills Installation

Install **globally** to `~/.agents/` using required flags:

```bash
# Install all skills from a repository
npx skills add <owner/repo> -a github-copilot -g

# Install a specific skill
npx skills add <owner/repo> -s <skill-name> -a github-copilot -g
```

**Required flags:**
- `-g` - Installs to home directory (REQUIRED for lockfile tracking)
- `-a github-copilot` - Uses universal `.agents` path (ensures compatibility)

## Sync Commands

### `pnpm sync-from-home` (Home → Repository)

Syncs changes FROM home TO repository:
- Copies `.skill-lock.json` from `~/.agents/` to repo `.agents/`
- Copies skill folders from `~/.agents/skills/` to repo `.agents/skills/`
- **Use after**: Installing/updating skills to prepare for git commit

### `pnpm sync-to-home` (Repository → Home)

Syncs changes FROM repository TO home:
- Copies `.skill-lock.json` and skills from repo to `~/.agents/`
- **Use when**: New machine, fresh agent environment, or restoring skills
- Makes skills immediately available globally

## Common Workflows

### Adding a New Skill

```bash
# 1. First time: restore existing skills to home
pnpm sync-to-home

# 2. Install skill with -g flag (REQUIRED!)
npx skills add <repo> -s <skill> -a github-copilot -g

# 3. Sync updated lockfile back to repo
pnpm sync-from-home

# 4. Commit changes
git add .agents/
git commit -m "Add <skill-name> skill"
```

**Critical**: The `-g` flag is mandatory. Without it:
- Skill installs to local `.agents/` instead of `~/.agents/`
- Global lockfile won't update
- Skill won't be tracked properly

### Updating Skills

```bash
# 1. First time: sync to home if directory is empty
pnpm sync-to-home

# 2. Update skills
npx skills update
# or check for updates first
npx skills check

# 3. Sync back to repository
pnpm sync-from-home

# 4. Commit changes
git commit -am "Update skills"
```

### Syncing on New Machine or Fresh Agent

```bash
# 1. Clone repository
git clone <repo-url>
cd skills

# 2. ALWAYS run this first
pnpm sync-to-home

# 3. Skills are now available globally and ready for use
```

## Important Rules

- **Never** manually edit `.agents/.skill-lock.json` - managed by skills CLI
- **Always** use `-a github-copilot -g` flags when adding/updating skills
- Repository stores snapshot for version control and sharing
- For agents/fresh environments: **Always** run `pnpm sync-to-home` before making changes

## Troubleshooting

### Skill not installing?
- Verify `-g` flag is used
- Check `~/.agents/.skill-lock.json` exists
- Run `pnpm sync-to-home` first if starting fresh

### Lockfile not updating?
- Ensure `-g` flag is present
- Skills must install to `~/.agents/` not local `.agents/`
- Check if `pnpm sync-from-home` was run after installation

### Skills not available?
- Run `pnpm sync-to-home` to restore from repository
- Verify `~/.agents/skills/` contains skill folders
- Check `.skill-lock.json` has skill entry

## File Locations

```
Repository:
  .agents/
    .skill-lock.json    # Lockfile snapshot
    skills/             # Skill folders snapshot
  
Home Directory:
  ~/.agents/
    .skill-lock.json    # Active lockfile
    skills/             # Active skills (used by agents)
```
