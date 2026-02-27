# assign_to.py API Reference

Complete reference for the `frappe.desk.form.assign_to` module providing programmatic assignment operations.

## Table of Contents

1. [Module Overview](#module-overview)
2. [Function Reference](#function-reference)
3. [Usage Examples](#usage-examples)
4. [Error Handling](#error-handling)
5. [Integration Patterns](#integration-patterns)

## Module Overview

### Import

```python
from frappe.desk.form import assign_to
```

### Purpose

The assign_to module provides functions for:
- Creating assignments (ToDo records)
- Retrieving assignments for documents
- Removing/cancelling assignments
- Closing completed assignments
- Bulk assignment operations

### Key Features

- Automatic notification sending
- Document sharing when needed
- Permission validation
- Duplicate detection
- Reference document linking
- Comment creation on timeline

## Function Reference

### assign_to.get()

Get existing assignments for a document.

**Signature:**
```python
def get(args=None)
```

**Parameters:**
- `args` (dict, optional): Arguments dict or uses `frappe.local.form_dict`
  - `doctype` (str): DocType name
  - `name` (str): Document name

**Returns:**
```python
[
    {"owner": "user@example.com", "name": "TODO-0001"},
    {"owner": "user2@example.com", "name": "TODO-0002"}
]
```

**Example:**
```python
assignments = assign_to.get({
    "doctype": "Issue",
    "name": "ISS-001"
})
# Returns list of open assignments
```

**SQL Query:**
```sql
SELECT allocated_to as owner, name
FROM `tabToDo`
WHERE reference_type = %(doctype)s
  AND reference_name = %(name)s
  AND status NOT IN ('Cancelled', 'Closed')
LIMIT 5
```

---

### assign_to.add()

Create new assignment(s) for a document.

**Signature:**
```python
@frappe.whitelist()
def add(args=None, *, ignore_permissions=False)
```

**Parameters:**
- `args` (dict, optional): Assignment parameters or uses `frappe.local.form_dict`
  - `assign_to` (list): List of user emails to assign
  - `doctype` (str): DocType name
  - `name` (str): Document name
  - `description` (str, optional): Task description (HTML supported)
  - `priority` (str, optional): "High", "Medium" (default), or "Low"
  - `date` (str, optional): Due date (YYYY-MM-DD format)
  - `assigned_by` (str, optional): Assigner email (defaults to session user)
  - `assignment_rule` (str, optional): Assignment Rule name if created by rule
- `ignore_permissions` (bool): Skip permission checks

**Returns:**
```python
[
    {"owner": "user@example.com", "name": "TODO-0001"}
]
```

**Behavior:**
1. Checks for duplicate assignments
2. Validates document permissions
3. Creates ToDo document
4. Shares document if user lacks permission
5. Follows document if user has auto-follow enabled
6. Sends notification to assignee

**Example - Basic:**
```python
assign_to.add({
    "assign_to": ["user@example.com"],
    "doctype": "Issue",
    "name": "ISS-001",
    "description": "Please review this issue"
})
```

**Example - With Options:**
```python
assign_to.add({
    "assign_to": ["user1@example.com", "user2@example.com"],
    "doctype": "Sales Order",
    "name": "SO-001",
    "description": "Approve order for $10,000",
    "priority": "High",
    "date": "2024-02-15",
    "assigned_by": "manager@example.com"
})
```

**Example - Ignore Permissions:**
```python
# For system-level assignments
assign_to.add({
    "assign_to": ["support@example.com"],
    "doctype": "Issue",
    "name": "ISS-001",
    "description": "Auto-assigned by rule"
}, ignore_permissions=True)
```

**Duplicate Handling:**
```python
# If assignment already exists:
# - Skips creation
# - Shows message: "Already in the following Users ToDo list: user@example.com"
# - Returns existing assignments
```

**Sharing Behavior:**
```python
# If user lacks permission and sharing enabled:
# - Shares document with Read access
# - Shows message: "Shared with the following Users with Read access: user@example.com"

# If user lacks permission and sharing disabled:
# - Throws error: "User user@example.com is not permitted to access this document"
```

---

### assign_to.add_multiple()

Assign same users to multiple documents.

**Signature:**
```python
@frappe.whitelist()
def add_multiple(args=None)
```

**Parameters:**
- `args` (dict, optional): Parameters or uses `frappe.local.form_dict`
  - `assign_to` (list): List of user emails
  - `doctype` (str): DocType name
  - `name` (list): List of document names (JSON string)
  - Other parameters same as `add()`

**Example:**
```python
assign_to.add_multiple({
    "assign_to": ["reviewer@example.com"],
    "doctype": "Sales Order",
    "name": json.dumps(["SO-001", "SO-002", "SO-003"]),
    "description": "Batch review required"
})
```

**Behavior:**
- Calls `add()` for each document
- Processes sequentially
- Each gets same assignees and description

---

### assign_to.remove()

Cancel an assignment for a user.

**Signature:**
```python
@frappe.whitelist()
def remove(doctype, name, assign_to, ignore_permissions=False)
```

**Parameters:**
- `doctype` (str): DocType name
- `name` (str): Document name
- `assign_to` (str): User email to unassign
- `ignore_permissions` (bool): Skip permission checks

**Returns:**
```python
[
    {"owner": "remaining_user@example.com", "name": "TODO-0002"}
]
```

**Behavior:**
1. Validates document permissions
2. Finds open ToDo for user and document
3. Sets ToDo status to "Cancelled"
4. Clears `assigned_to` field on document (if exists)
5. Sends removal notification
6. Returns remaining assignments

**Example:**
```python
assign_to.remove("Issue", "ISS-001", "user@example.com")
```

**Internal Implementation:**
```python
# Calls set_status with status="Cancelled"
def remove(doctype, name, assign_to, ignore_permissions=False):
    return set_status(
        doctype, name, "", assign_to,
        status="Cancelled",
        ignore_permissions=ignore_permissions
    )
```

---

### assign_to.remove_multiple()

Remove assignments from multiple documents.

**Signature:**
```python
@frappe.whitelist()
def remove_multiple(doctype, names, ignore_permissions=False)
```

**Parameters:**
- `doctype` (str): DocType name
- `names` (str): JSON string of document names
- `ignore_permissions` (bool): Skip permission checks

**Example:**
```python
assign_to.remove_multiple(
    "Issue",
    json.dumps(["ISS-001", "ISS-002"]),
    ignore_permissions=True
)
```

**Behavior:**
- Gets assignments for each document
- Calls `remove()` for each assignee
- Processes all documents in list

---

### assign_to.close()

Close a completed assignment.

**Signature:**
```python
@frappe.whitelist()
def close(doctype: str, name: str, assign_to: str, ignore_permissions=False)
```

**Parameters:**
- `doctype` (str): DocType name
- `name` (str): Document name
- `assign_to` (str): User email (must be current user unless ignore_permissions)
- `ignore_permissions` (bool): Skip permission and user checks

**Returns:**
```python
[
    {"owner": "other_user@example.com", "name": "TODO-0002"}
]
```

**Behavior:**
1. Validates user is assignee (unless ignore_permissions)
2. Sets ToDo status to "Closed"
3. Clears `assigned_to` field on document (if exists)
4. Sends completion notification
5. Returns remaining assignments

**Example:**
```python
# User closing their own assignment
assign_to.close("Issue", "ISS-001", frappe.session.user)
```

**Permission Check:**
```python
if assign_to != frappe.session.user:
    frappe.throw("Only the assignee can complete this to-do.")
```

**Example - System Close:**
```python
# For automated completion
assign_to.close(
    "Task", "TASK-001", "user@example.com",
    ignore_permissions=True
)
```

---

### assign_to.close_all_assignments()

Close all open assignments for a document.

**Signature:**
```python
def close_all_assignments(doctype, name, ignore_permissions=False)
```

**Parameters:**
- `doctype` (str): DocType name
- `name` (str): Document name
- `ignore_permissions` (bool): Skip permission checks

**Returns:**
- `True` if assignments were closed
- `False` if no assignments found

**Behavior:**
- Finds all non-cancelled assignments
- Closes each one
- Useful for bulk completion

**Example:**
```python
# Close all when document is completed
def on_update(doc):
    if doc.status == "Completed":
        from frappe.desk.form import assign_to
        assign_to.close_all_assignments(
            doc.doctype, doc.name,
            ignore_permissions=True
        )
```

---

### assign_to.clear()

Cancel all assignments for a document.

**Signature:**
```python
def clear(doctype, name, ignore_permissions=False)
```

**Parameters:**
- `doctype` (str): DocType name
- `name` (str): Document name
- `ignore_permissions` (bool): Skip permission checks

**Returns:**
- `True` if assignments were cleared
- `False` if no assignments found

**Behavior:**
- Finds all assignments (any status)
- Cancels each one
- Clears `assigned_to` field
- Used for cleanup

**Example:**
```python
# Clear before deleting document
def before_delete(doc):
    from frappe.desk.form import assign_to
    assign_to.clear(doc.doctype, doc.name, ignore_permissions=True)
```

---

### Internal: assign_to.set_status()

Internal function for status changes.

**Signature:**
```python
def set_status(doctype, name, todo=None, assign_to=None, status="Cancelled", ignore_permissions=False)
```

**Parameters:**
- `doctype` (str): DocType name
- `name` (str): Document name
- `todo` (str, optional): Specific ToDo name
- `assign_to` (str, optional): User email
- `status` (str): "Cancelled" or "Closed"
- `ignore_permissions` (bool): Skip checks

**Behavior:**
- Used by remove() and close()
- Updates ToDo status
- Clears document field if status is "Cancelled" or "Closed"
- Sends notification

---

### Internal: notify_assignment()

Send assignment notification.

**Signature:**
```python
def notify_assignment(assigned_by, allocated_to, doc_type, doc_name, action="CLOSE", description=None)
```

**Parameters:**
- `assigned_by` (str): Assigner email
- `allocated_to` (str): Assignee email
- `doc_type` (str): DocType
- `doc_name` (str): Document name
- `action` (str): "ASSIGN" or "CLOSE"
- `description` (str, optional): Task description HTML

**Behavior:**
- Skips if assigned_by == allocated_to
- Skips if user disabled
- Creates notification log
- Enqueues email sending

## Usage Examples

### Example 1: Simple Assignment

```python
from frappe.desk.form import assign_to

# Assign single user
assign_to.add({
    "assign_to": ["user@example.com"],
    "doctype": "Issue",
    "name": "ISS-001",
    "description": "Please investigate"
})
```

### Example 2: Multiple Assignees

```python
# Assign to team
assign_to.add({
    "assign_to": [
        "user1@example.com",
        "user2@example.com",
        "user3@example.com"
    ],
    "doctype": "Project",
    "name": "PROJ-001",
    "description": "Review project plan",
    "priority": "High",
    "date": "2024-02-01"
})
```

### Example 3: Get and Display Assignments

```python
# Get current assignments
assignments = assign_to.get({
    "doctype": "Issue",
    "name": "ISS-001"
})

for assignment in assignments:
    print(f"Assigned to: {assignment['owner']}")
```

### Example 4: Complete Assignment

```python
# User completes their task
assign_to.close(
    "Issue", "ISS-001",
    frappe.session.user
)
```

### Example 5: Bulk Assignment

```python
# Assign reviewer to multiple documents
issues = frappe.get_all("Issue",
    filters={"status": "Open", "priority": "High"},
    pluck="name"
)

assign_to.add_multiple({
    "assign_to": ["reviewer@example.com"],
    "doctype": "Issue",
    "name": json.dumps(issues),
    "description": "High priority review"
})
```

### Example 6: Document Lifecycle Integration

```python
class CustomDocType(Document):
    def on_submit(self):
        # Auto-assign for approval
        from frappe.desk.form import assign_to
        
        assign_to.add({
            "assign_to": [self.approver],
            "doctype": self.doctype,
            "name": self.name,
            "description": f"Please approve {self.name}",
            "priority": "High"
        }, ignore_permissions=True)
    
    def on_cancel(self):
        # Clear assignments
        from frappe.desk.form import assign_to
        assign_to.clear(
            self.doctype, self.name,
            ignore_permissions=True
        )
```

### Example 7: Conditional Assignment

```python
def assign_based_on_value(doc):
    from frappe.desk.form import assign_to
    
    if doc.grand_total > 10000:
        assignee = "senior.manager@example.com"
        priority = "High"
    elif doc.grand_total > 5000:
        assignee = "manager@example.com"
        priority = "Medium"
    else:
        assignee = "associate@example.com"
        priority = "Low"
    
    assign_to.add({
        "assign_to": [assignee],
        "doctype": doc.doctype,
        "name": doc.name,
        "description": f"Review order worth {doc.grand_total}",
        "priority": priority
    }, ignore_permissions=True)
```

### Example 8: Reassignment

```python
def reassign(doctype, name, old_user, new_user):
    from frappe.desk.form import assign_to
    
    # Remove old assignment
    assign_to.remove(doctype, name, old_user, ignore_permissions=True)
    
    # Add new assignment
    assign_to.add({
        "assign_to": [new_user],
        "doctype": doctype,
        "name": name,
        "description": f"Reassigned from {old_user}"
    }, ignore_permissions=True)
```

### Example 9: Escalation

```python
def escalate_overdue_assignments():
    from frappe.utils import today, add_days
    from frappe.desk.form import assign_to
    
    # Find overdue todos
    overdue = frappe.get_all("ToDo",
        filters={
            "status": "Open",
            "date": ["<", add_days(today(), -2)]
        },
        fields=["reference_type", "reference_name", "allocated_to"]
    )
    
    for todo in overdue:
        # Assign to manager
        assign_to.add({
            "assign_to": ["manager@example.com"],
            "doctype": todo.reference_type,
            "name": todo.reference_name,
            "description": f"Escalated: Overdue assignment for {todo.allocated_to}",
            "priority": "High"
        }, ignore_permissions=True)
```

### Example 10: Status-Based Cleanup

```python
def cleanup_completed_assignments(doctype):
    """Close assignments for completed documents"""
    from frappe.desk.form import assign_to
    
    completed = frappe.get_all(doctype,
        filters={"status": "Completed"},
        pluck="name"
    )
    
    for name in completed:
        assign_to.close_all_assignments(
            doctype, name,
            ignore_permissions=True
        )
```

## Error Handling

### DuplicateToDoError

Raised when assignment already exists.

```python
from frappe.desk.form.assign_to import DuplicateToDoError

try:
    assign_to.add({...})
except DuplicateToDoError:
    frappe.msgprint("Assignment already exists")
```

**Note:** `add()` function handles duplicates internally and shows message instead of raising exception.

### PermissionError

```python
try:
    assign_to.add({...})
except frappe.PermissionError:
    frappe.msgprint("You don't have permission to assign")
```

### DoesNotExistError

When document doesn't exist:

```python
try:
    assign_to.add({
        "assign_to": ["user@example.com"],
        "doctype": "Issue",
        "name": "NONEXISTENT"
    })
except frappe.DoesNotExistError:
    frappe.msgprint("Document not found")
```

### User Not Found

```python
# If user doesn't exist, assignment fails silently in some cases
# Always validate user exists:

if frappe.db.exists("User", user_email):
    assign_to.add({...})
else:
    frappe.msgprint(f"User {user_email} not found")
```

## Integration Patterns

### Pattern 1: Hook Integration

```python
# hooks.py
doc_events = {
    "Issue": {
        "on_submit": "myapp.utils.auto_assign_issue"
    }
}

# myapp/utils.py
def auto_assign_issue(doc, method):
    from frappe.desk.form import assign_to
    
    if doc.priority == "High":
        assign_to.add({
            "assign_to": ["urgent_team@example.com"],
            "doctype": doc.doctype,
            "name": doc.name,
            "description": "Urgent issue requires attention",
            "priority": "High"
        }, ignore_permissions=True)
```

### Pattern 2: Workflow Integration

```python
class MyDocument(Document):
    def before_transition(self, transition):
        """Assign before workflow transition"""
        from frappe.desk.form import assign_to
        
        if transition.next_state == "Pending Approval":
            approver = self.get_approver()
            assign_to.add({
                "assign_to": [approver],
                "doctype": self.doctype,
                "name": self.name,
                "description": f"Approve {self.name}",
                "priority": "High"
            }, ignore_permissions=True)
    
    def after_transition(self, transition):
        """Clear assignments after transition"""
        from frappe.desk.form import assign_to
        
        if transition.next_state in ["Approved", "Rejected"]:
            assign_to.clear(
                self.doctype, self.name,
                ignore_permissions=True
            )
```

### Pattern 3: Scheduled Assignment Check

```python
# hooks.py
scheduler_events = {
    "hourly": [
        "myapp.tasks.check_pending_assignments"
    ]
}

# myapp/tasks.py
def check_pending_assignments():
    """Check for documents needing assignment"""
    from frappe.desk.form import assign_to
    
    unassigned = frappe.get_all("Issue",
        filters={
            "status": "Open",
            "_assign": ["is", "not set"]
        },
        pluck="name"
    )
    
    for issue_name in unassigned:
        assign_to.add({
            "assign_to": get_next_agent(),
            "doctype": "Issue",
            "name": issue_name,
            "description": "Auto-assigned unassigned issue"
        }, ignore_permissions=True)
```

### Pattern 4: API Endpoint

```python
# api.py
@frappe.whitelist()
def assign_document(doctype, name, users):
    """API endpoint for assignments"""
    from frappe.desk.form import assign_to
    
    users = frappe.parse_json(users)
    
    return assign_to.add({
        "assign_to": users,
        "doctype": doctype,
        "name": name,
        "description": "Assigned via API"
    })
```

### Pattern 5: Bulk Processing

```python
def bulk_assign_by_territory():
    """Assign leads to territory managers"""
    from frappe.desk.form import assign_to
    
    territories = frappe.get_all("Territory",
        filters={"is_group": 0},
        fields=["name", "territory_manager"]
    )
    
    for territory in territories:
        if not territory.territory_manager:
            continue
        
        leads = frappe.get_all("Lead",
            filters={
                "status": "Open",
                "territory": territory.name
            },
            pluck="name"
        )
        
        if leads:
            assign_to.add_multiple({
                "assign_to": [territory.territory_manager],
                "doctype": "Lead",
                "name": json.dumps(leads),
                "description": f"Leads in {territory.name}"
            })
```
