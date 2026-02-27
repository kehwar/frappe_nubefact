---
name: frappe-doctype-customization
description: Practical patterns for customizing core Frappe/ERPNext doctypes via custom apps. Use when adding custom fields to standard doctypes (Employee, Item, Sales Person, etc.), implementing controller overrides, managing field migrations, maintaining backward compatibility with legacy fields, or structuring doctype customization modules. Covers idempotent setup functions, migration patches, package structure, and hook registration.
---

# Frappe DocType Customization

Proven patterns for extending core Frappe/ERPNext doctypes through custom apps without modifying framework code.

## When to Use This Approach

- Adding custom fields to standard doctypes (Employee, Item, Customer, Sales Order, etc.)
- Overriding doctype controllers with custom business logic
- Migrating from legacy custom field names to canonical ones
- Maintaining backward compatibility during field transitions
- Structuring reusable customization modules

## Core Pattern: Setup Function + Patch + Hook

### 1. Setup Function (Idempotent Field Creation)

Create `custom/doctype/{doctype_name}/{doctype_name}_setup.py`:

```python
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup_{doctype_name}() -> None:
    fields_to_create = []
    
    # Check if field exists before adding
    if not frappe.db.exists(
        "Custom Field",
        {"dt": "Target DocType", "fieldname": "new_field"},
    ):
        fields_to_create.append({
            "fieldname": "new_field",
            "fieldtype": "Check",
            "label": "New Field Label",
            "insert_after": "existing_field",
            "default": "0",
        })
    
    if not fields_to_create:
        return
    
    create_custom_fields(
        {"Target DocType": fields_to_create},
        update=True
    )
```

**Key characteristics:**
- Idempotent: safe to run multiple times
- Checks field existence before creating (avoids duplicates)
- Returns early if no work needed
- Uses `update=True` for upsert behavior

### 2. Migration Patch (One-Time Data Migration)

Create `patches/YYYY/YYYYMMDD_descriptive_name.py`:

```python
import frappe
from your_app.custom.doctype.employee.employee_setup import setup_employee

def _hide_legacy_field() -> None:
    """Hide legacy custom field without deleting data."""
    custom_field_name = frappe.db.get_value(
        "Custom Field",
        {"dt": "Employee", "fieldname": "old_field_name"},
    )
    
    if not custom_field_name:
        return
    
    frappe.db.set_value(
        "Custom Field",
        custom_field_name,
        "hidden",
        1,
        update_modified=False,
    )

def _copy_legacy_data_to_new_field() -> None:
    """Copy data from legacy field to canonical field."""
    if not frappe.db.has_column("Employee", "new_field"):
        return
    
    if not frappe.db.has_column("Employee", "old_field"):
        return
    
    rows = frappe.get_all(
        "Employee",
        fields=["name", "old_field"],
    )
    
    for row in rows:
        frappe.db.set_value(
            "Employee",
            row.name,
            "new_field",
            row.old_field,
            update_modified=False,
        )

def execute():
    setup_employee()
    _hide_legacy_field()
    _copy_legacy_data_to_new_field()
```

Register in `patches.txt`:
```
your_app.patches.YYYY.YYYYMMDD_descriptive_name
```

**Migration best practices:**
- Call setup function first
- Check column existence before data operations
- Hide legacy fields instead of deleting (preserves data for rollback)
- Use `update_modified=False` to avoid version noise
- Private helper functions for clarity

### 3. Hook Registration

In `hooks.py`:

```python
# Override doctype controller
override_doctype_class = {
    "Employee": "your_app.custom.doctype.employee.employee.CustomEmployee",
}

# Run setup on fresh installs
after_install = "your_app.custom.doctype.employee.employee_setup.setup_employee"
```

## Customization Package Structure

Organize customizations as packages (not flat modules):

```
your_app/
└── custom/
    └── doctype/
        └── employee/
            ├── __init__.py          # Export public symbols
            ├── employee.py          # Controller override
            └── employee_setup.py    # Setup function
```

### Package `__init__.py`

```python
from .employee import CustomEmployee, helper_function
from .employee_setup import setup_employee
```

### Controller Override (`employee.py`)

```python
import frappe
from erpnext.setup.doctype.employee.employee import Employee

class CustomEmployee(Employee):
    
    def validate(self):
        super().validate()
        self.sync_canonical_to_legacy()
    
    def sync_canonical_to_legacy(self):
        """Maintain backward compatibility by syncing new → old field."""
        if not self.meta.has_field("old_field"):
            return
        
        self.old_field = self.new_field
```

**Why package structure:**
- Clear separation: controller logic vs. setup logic
- Easier testing and imports
- Supports future expansion (utils, tests, etc.)

## Backward Compatibility Pattern

When replacing a legacy field with a canonical one:

### In Controller (Sync New → Legacy)

```python
def sync_canonical_to_legacy(self):
    """Write canonical field value back to legacy field."""
    if not self.meta.has_field("legacy_field"):
        return
    
    self.legacy_field = self.canonical_field
```

Call from `validate()` or `on_change()` hook.

### In Migration Patch (Copy Legacy → Canonical)

```python
def _copy_legacy_to_canonical():
    """One-time data migration from legacy to canonical field."""
    # Check both columns exist
    # Iterate and copy values
    # See full example in Migration Patch section above
```

**Result:** Code reads/writes canonical field; legacy field stays in sync automatically.

## Child Table Custom Fields

Adding fields to child table doctypes:

### 1. Add Field to Child DocType JSON

Edit `your_app/doctype/child_doctype/child_doctype.json`:

```json
{
  "fields": [
    {
      "fieldname": "new_field",
      "fieldtype": "Check",
      "label": "New Field",
      "default": "0"
    }
  ]
}
```

Run `bench migrate` to apply schema changes.

### 2. Controller Sync (if needed)

```python
from frappe.model.document import Document

class ChildDocType(Document):
    
    def validate(self):
        if self.meta.has_field("legacy_field"):
            self.legacy_field = self.new_field
```

**Note:** Child table fields are managed via JSON schema, not Custom Field records (since child tables are `istable=1`).

## Common Tasks

### Add Check Field with Default

```python
{
    "fieldname": "enabled",
    "fieldtype": "Check",
    "label": "Enabled",
    "insert_after": "status",
    "default": "0",
}
```

### Add Table Field (Child Relationship)

```python
{
    "fieldname": "sales_team",
    "fieldtype": "Table",
    "label": "Sales Team",
    "options": "Employee Sales Person",  # Child doctype name
    "insert_after": "previous_field",
}
```

### Hide Existing Field

```python
frappe.db.set_value(
    "Custom Field",
    field_name,
    "hidden",
    1,
    update_modified=False,
)
```

### Check Field Existence

```python
exists = frappe.db.exists(
    "Custom Field",
    {"dt": "Employee", "fieldname": "my_field"}
)
```

### Check Column Existence (Before Data Operations)

```python
if frappe.db.has_column("Employee", "my_field"):
    # Safe to query/update this column
```

## Best Practices

1. **Always use setup functions** - Never create fields directly in patches
2. **Check before creating** - Use `frappe.db.exists()` to avoid duplicates
3. **Hide, don't delete** - Preserve legacy fields for rollback capability
4. **Sync for compatibility** - Write canonical → legacy in controller validate
5. **Package structure** - Separate controller from setup logic
6. **Register after_install** - Ensure fresh installs create fields automatically
7. **Use update_modified=False** - Avoid version control noise in data migrations

## Troubleshooting

**Field not appearing:** Check `bench migrate` output, verify hook registration, confirm field isn't hidden.

**Duplicate field error:** Setup function should check existence; if error persists, manually delete duplicate Custom Field record.

**Data not migrating:** Verify column existence with `frappe.db.has_column()` before querying.

**Legacy code breaks:** Implement backward compat sync in controller; don't remove legacy field immediately.

## References

- Frappe Custom Field API: `frappe.custom.doctype.custom_field.custom_field.create_custom_fields()`
- DocType Override: Use `override_doctype_class` hook
- Migration Patches: Add to `patches.txt` in `[post_model_sync]` section
