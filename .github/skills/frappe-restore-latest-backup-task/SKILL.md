---
name: frappe-restore-latest-backup-task
description: Automated workflow for restoring the latest Frappe/ERPNext backup with proper database configuration, migrations, and password reset. Use when users request "restore latest backup", "restore backup", or need to recover from a backup file.
---

# Restore Latest Backup Task

Automated workflow for restoring Frappe/ERPNext backups following best practices.

## When to Use

Use this skill when users request:
- "Restore the latest backup"
- "Restore backup"
- "Restore from backup"
- Any backup restoration task

## Prerequisites

- Frappe bench environment at `/workspace/development/frappe-bench`
- MariaDB accessible at host `mariadb` with root password `123`
- Target site: `development.localhost`
- Backup files in `backups/` directory

## Complete Restoration Workflow

### 1. Find Latest Backup

```bash
cd /workspace/development/frappe-bench && \
LATEST_DB=$(find backups -maxdepth 1 -type f -name '*-database.sql.gz' -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-) && \
TS=$(basename "$LATEST_DB" | cut -d'-' -f1) && \
echo "TIMESTAMP=$TS" && \
echo "DB_FILE=$LATEST_DB"
```

Extract the timestamp prefix (e.g., `20260219_000036`) for use in subsequent commands.

### 1.1 Verify Companion File Archives

```bash
cd /workspace/development/frappe-bench && \
PUB="backups/TIMESTAMP-gruposoldamundo_frappe_cloud-files.tar" && \
PRI="backups/TIMESTAMP-gruposoldamundo_frappe_cloud-private-files.tar" && \
([ -f "$PUB" ] && echo "PUBLIC=present:$PUB" || echo "PUBLIC=missing:$PUB") && \
([ -f "$PRI" ] && echo "PRIVATE=present:$PRI" || echo "PRIVATE=missing:$PRI")
```

If `PUBLIC=missing`, restore with private files only (or database only if both are missing).

### 2. Check Database Size

```bash
ls -lh backups/TIMESTAMP-gruposoldamundo_frappe_cloud-database.sql.gz
```

**Decision point**: If compressed size > 100MB, proceed with MariaDB configuration.

### 3. Configure MariaDB Memory

Required for large databases to prevent packet size errors.

```bash
mariadb -h mariadb -u root -p123 -e "SET GLOBAL max_allowed_packet=536870912; SHOW GLOBAL VARIABLES LIKE 'max_allowed_packet';"
```

**Expected output**: `max_allowed_packet | 536870912` (512MB)

**Note**: This setting is lost on container restart. For persistence, add to docker-compose.yml.

### 4. Restore Database and Files

When both file archives exist:

```bash
cd /workspace/development/frappe-bench && \
bench --site development.localhost restore \
    --db-root-password 123 \
    "backups/TIMESTAMP-gruposoldamundo_frappe_cloud-database.sql.gz" \
    --with-public-files "backups/TIMESTAMP-gruposoldamundo_frappe_cloud-files.tar" \
    --with-private-files "backups/TIMESTAMP-gruposoldamundo_frappe_cloud-private-files.tar"
```

When public files are missing but private files exist:

```bash
cd /workspace/development/frappe-bench && \
bench --site development.localhost restore \
    --db-root-password 123 \
    "backups/TIMESTAMP-gruposoldamundo_frappe_cloud-database.sql.gz" \
    --with-private-files "backups/TIMESTAMP-gruposoldamundo_frappe_cloud-private-files.tar"
```

**Success indicators**:
- "Site development.localhost has been restored with files"
- No error messages about packet size or access denied

### 5. Run Migrations

```bash
bench --site development.localhost migrate
```

Syncs database schema with current app versions. **Critical** - skipping this causes errors.

### 6. Set Admin Password

```bash
bench --site development.localhost set-admin-password admin
```

Resets password to development standard for easy access.

## Automated Script

For quick execution without manual intervention:

```bash
#!/bin/bash
set -e  # Exit on error

BENCH_PATH="/workspace/development/frappe-bench"
SITE="development.localhost"
DB_PASSWORD="123"
ADMIN_PASSWORD="admin"

cd "$BENCH_PATH"

# Find latest backup
LATEST=$(find backups -maxdepth 1 -type f -name '*-database.sql.gz' -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-)
if [ -z "$LATEST" ]; then
    echo "Error: No backup files found"
    exit 1
fi

# Extract timestamp
TIMESTAMP=$(basename "$LATEST" | cut -d'-' -f1)
echo "Found latest backup: $TIMESTAMP"

# Check if files exist
DB_FILE="backups/${TIMESTAMP}-gruposoldamundo_frappe_cloud-database.sql.gz"
PUBLIC_FILES="backups/${TIMESTAMP}-gruposoldamundo_frappe_cloud-files.tar"
PRIVATE_FILES="backups/${TIMESTAMP}-gruposoldamundo_frappe_cloud-private-files.tar"

# Check database size
SIZE=$(stat -f%z "$DB_FILE" 2>/dev/null || stat -c%s "$DB_FILE" 2>/dev/null)
SIZE_MB=$((SIZE / 1024 / 1024))
echo "Database size: ${SIZE_MB}MB (compressed)"

# Configure MariaDB if needed
if [ $SIZE_MB -gt 100 ]; then
    echo "Configuring MariaDB for large database..."
    mariadb -h mariadb -u root -p$DB_PASSWORD -e \
        "SET GLOBAL max_allowed_packet=536870912;"
fi

# Restore
echo "Restoring database and files..."
bench --site $SITE restore \
    --db-root-password $DB_PASSWORD \
    "$DB_FILE" \
    $([ -f "$PUBLIC_FILES" ] && echo "--with-public-files $PUBLIC_FILES") \
    $([ -f "$PRIVATE_FILES" ] && echo "--with-private-files $PRIVATE_FILES")

# Migrate
echo "Running migrations..."
bench --site $SITE migrate

# Set password
echo "Setting admin password..."
bench --site $SITE set-admin-password $ADMIN_PASSWORD

echo "✅ Restore complete!"
echo "Site: http://development.localhost:8000"
echo "Username: Administrator"
echo "Password: $ADMIN_PASSWORD"
```

Save as `restore-latest.sh`, make executable with `chmod +x restore-latest.sh`, then run `./restore-latest.sh`.

## Common Issues

### Packet Size Error

**Symptom**: `Got a packet bigger than 'max_allowed_packet' bytes`

**Solution**: Increase `max_allowed_packet` (step 3)

### Access Denied for Database User

**Symptom**: `Access denied for user '_abc123'@'%'`

**Cause**: Database user lost after MariaDB container restart

**Solution**: Drop and recreate the site, or manually recreate the database user:
```bash
mariadb -h mariadb -u root -p123 -e \
    "CREATE USER IF NOT EXISTS '_abc123'@'%' IDENTIFIED BY 'password'; \
     GRANT ALL PRIVILEGES ON \`_abc123\`.* TO '_abc123'@'%'; \
     FLUSH PRIVILEGES;"
```

### Missing Files

**Symptom**: Backup restored but files missing from restoration

**Solution**: Check if file tarballs exist. If missing, restore database only:
```bash
bench --site development.localhost restore \
    --db-root-password 123 \
    "backups/TIMESTAMP-database.sql.gz"
```

### Encryption Key Mismatch

**Symptom**: Errors about encrypted fields after restore to a recreated site

**Solution**: Set encryption_key from `site_config_backup.json` before restoring:
```bash
# Extract key from backup
cat backups/TIMESTAMP-site_config_backup.json

# Set on site before restore
bench --site development.localhost set-config encryption_key "KEY_FROM_BACKUP"
```

## Best Practices

1. **Always check database size first** - Prevents mid-restore failures
2. **Use MariaDB configuration for large databases** - 512MB packet size handles most cases
3. **Never skip migrations** - Database schema must match code
4. **Keep site_config_backup.json** - Essential for encryption_key recovery
5. **Test restore success** - Try logging in at http://development.localhost:8000

## Implementation Notes

When implementing this workflow:

1. **Use parallel operations where safe** - Finding latest backup and checking size can happen together
2. **Provide progress updates** - Users should know which step is executing
3. **Handle errors gracefully** - Each step should check for success
4. **Use absolute paths** - Prevents ambiguity in file locations
5. **Verify completion** - Confirm admin password was set and migrations completed
6. **Prefer single-shell one-liners for discovery** - Avoid multi-line partial execution in persistent terminals

## Quick Reference

```bash
# Complete one-liner (replace TIMESTAMP)
cd /workspace/development/frappe-bench && \
mariadb -h mariadb -u root -p123 -e "SET GLOBAL max_allowed_packet=536870912;" && \
bench --site development.localhost restore --db-root-password 123 \
    "backups/TIMESTAMP-gruposoldamundo_frappe_cloud-database.sql.gz" \
    --with-public-files "backups/TIMESTAMP-gruposoldamundo_frappe_cloud-files.tar" \
    --with-private-files "backups/TIMESTAMP-gruposoldamundo_frappe_cloud-private-files.tar" && \
bench --site development.localhost migrate && \
bench --site development.localhost set-admin-password admin
```
