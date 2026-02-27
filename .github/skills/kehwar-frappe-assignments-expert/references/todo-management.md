# ToDo Management Reference

Complete guide to working with ToDo documents for task assignment and tracking.

## Table of Contents

1. [ToDo Structure](#todo-structure)
2. [Creating ToDo](#creating-todo)
3. [Querying ToDo](#querying-todo)
4. [Updating ToDo](#updating-todo)
5. [Permissions](#permissions)
6. [Lifecycle and Hooks](#lifecycle-and-hooks)
7. [Best Practices](#best-practices)

## ToDo Structure

### Fields

```python
{
    "doctype": "ToDo",
    "name": "TODO-0001",                    # Auto-generated
    
    # Assignment
    "allocated_to": "user@example.com",     # Required: assignee
    "assigned_by": "admin@example.com",     # Auto-set: who created
    "assigned_by_full_name": "John Doe",    # Read-only
    
    # Reference
    "reference_type": "Issue",              # Linked DocType
    "reference_name": "ISS-001",            # Linked document
    
    # Task details
    "description": "Please review this",    # Required: HTML supported
    "priority": "Medium",                   # High | Medium | Low
    "status": "Open",                       # Open | Closed | Cancelled
    "date": "2024-02-01",                   # Due date
    
    # Optional
    "assignment_rule": "Support Rule",      # If created by rule
    "role": "Support Team",                 # Role-based assignment (legacy)
    "sender": "email@example.com",          # For email-created todos
    "color": "#FF0000"                      # UI color coding
}
```

### Field Types

- **allocated_to**: Link to User (required)
- **assigned_by**: Link to User (auto-filled)
- **assigned_by_full_name**: Read Only (auto-filled)
- **assignment_rule**: Link to Assignment Rule
- **color**: Color picker
- **date**: Date field
- **description**: Text Editor (HTML)
- **priority**: Select (High, Medium, Low)
- **reference_name**: Dynamic Link
- **reference_type**: Link to DocType
- **role**: Link to Role (deprecated feature)
- **sender**: Data field
- **status**: Select (Open, Closed, Cancelled)

## Creating ToDo

### Method 1: Direct Insert

```python
todo = frappe.get_doc({
    "doctype": "ToDo",
    "allocated_to": "user@example.com",
    "description": "Complete the review",
    "priority": "High",
    "status": "Open",
    "date": frappe.utils.add_days(frappe.utils.today(), 7)
})
todo.insert()
```

### Method 2: With Reference

```python
todo = frappe.get_doc({
    "doctype": "ToDo",
    "allocated_to": "user@example.com",
    "assigned_by": frappe.session.user,
    "reference_type": "Issue",
    "reference_name": "ISS-001",
    "description": "Please resolve this issue",
    "priority": "Medium",
    "status": "Open"
})
todo.insert()
```

### Method 3: Via assign_to Module

```python
from frappe.desk.form import assign_to

# Recommended approach
assign_to.add({
    "assign_to": ["user@example.com"],
    "doctype": "Issue",
    "name": "ISS-001",
    "description": "Please review",
    "priority": "High"
})
```

### Method 4: Bulk Creation

```python
from frappe.desk.form import assign_to

assign_to.add_multiple({
    "assign_to": ["user1@example.com", "user2@example.com"],
    "doctype": "Issue",
    "name": ["ISS-001", "ISS-002", "ISS-003"],
    "description": "Batch assignment"
})
```

### Auto-filled Fields

When inserting ToDo:
- `assigned_by`: Set to `frappe.session.user` if not provided
- `assigned_by_full_name`: Populated from User's full_name
- `status`: Defaults to "Open" if not specified
- `priority`: Defaults to "Medium" if not specified

### Validation

On insert/update:
- Creates comment on reference document
- Updates `_assign` field on reference document
- Validates allocated_to is valid user
- Checks if duplicate exists (via assign_to.add)

## Querying ToDo

### Get All Assignments for User

```python
todos = frappe.get_all("ToDo",
    filters={"allocated_to": "user@example.com", "status": "Open"},
    fields=["name", "description", "reference_type", "reference_name", "priority", "date"],
    order_by="date asc, priority desc"
)
```

### Get Assignments for Document

```python
todos = frappe.get_all("ToDo",
    filters={
        "reference_type": "Issue",
        "reference_name": "ISS-001",
        "status": ("!=", "Cancelled")
    },
    fields=["allocated_to", "status", "priority"]
)
```

### Get Open Assignments Count

```python
count = frappe.db.count("ToDo",
    filters={
        "allocated_to": "user@example.com",
        "status": "Open"
    }
)
```

### Get Overdue Tasks

```python
from frappe.utils import today

overdue = frappe.get_all("ToDo",
    filters={
        "allocated_to": "user@example.com",
        "status": "Open",
        "date": ["<", today()]
    },
    fields=["*"],
    order_by="date asc"
)
```

### Get Tasks by Priority

```python
high_priority = frappe.get_all("ToDo",
    filters={
        "allocated_to": "user@example.com",
        "status": "Open",
        "priority": "High"
    },
    fields=["name", "description", "date"]
)
```

### Get Tasks Created by Assignment Rule

```python
rule_todos = frappe.get_all("ToDo",
    filters={
        "assignment_rule": ("is", "set"),
        "status": "Open"
    },
    fields=["allocated_to", "reference_type", "reference_name", "assignment_rule"]
)
```

### Complex Query with Multiple Conditions

```python
todos = frappe.get_all("ToDo",
    filters={
        "allocated_to": "user@example.com",
        "status": "Open",
        "priority": ["in", ["High", "Medium"]],
        "date": [">=", frappe.utils.today()],
        "reference_type": ["!=", ""]
    },
    fields=["*"],
    order_by="priority desc, date asc",
    limit=20
)
```

### Get User's ToDo List (API Method)

```python
# Uses built-in method with permission checks
from frappe.desk.doctype.todo.todo import ToDo

owners = ToDo.get_owners(filters={
    "status": "Open",
    "priority": "High"
})
# Returns list of allocated_to emails
```

## Updating ToDo

### Update Status

```python
todo = frappe.get_doc("ToDo", "TODO-0001")
todo.status = "Closed"
todo.save()
```

### Update Due Date

```python
frappe.db.set_value("ToDo", "TODO-0001", "date", "2024-03-01")
```

### Update Priority

```python
todo = frappe.get_doc("ToDo", "TODO-0001")
todo.priority = "High"
todo.save()
```

### Bulk Status Update

```python
todos = frappe.get_all("ToDo",
    filters={"allocated_to": "old_user@example.com", "status": "Open"},
    pluck="name"
)

for todo_name in todos:
    frappe.db.set_value("ToDo", todo_name, "status", "Cancelled")
```

### Reassign ToDo

```python
# Cancel old
old_todo = frappe.get_doc("ToDo", "TODO-0001")
old_todo.status = "Cancelled"
old_todo.save()

# Create new
from frappe.desk.form import assign_to
assign_to.add({
    "assign_to": ["new_user@example.com"],
    "doctype": old_todo.reference_type,
    "name": old_todo.reference_name,
    "description": old_todo.description
})
```

### Update via assign_to Module

```python
from frappe.desk.form import assign_to

# Close assignment
assign_to.close("Issue", "ISS-001", "user@example.com")

# Remove assignment
assign_to.remove("Issue", "ISS-001", "user@example.com")

# Clear all assignments
assign_to.clear("Issue", "ISS-001")
```

## Permissions

### Permission Logic

ToDo permissions use custom `has_permission` and `permission_query_conditions` hooks.

**User can view ToDo if:**
1. User has role permission for ToDo DocType, OR
2. User is the `allocated_to` user, OR
3. User is the `assigned_by` user

**Administrator:**
- Bypasses all permission checks
- Can view all ToDo documents

### Permission Query Implementation

```python
def get_permission_query_conditions(user):
    """Filter ToDo list based on user"""
    if not user:
        user = frappe.session.user
    
    # Check if user has role permissions
    todo_roles = frappe.permissions.get_doctype_roles("ToDo")
    todo_roles = set(todo_roles) - set(AUTOMATIC_ROLES)
    
    if any(check in todo_roles for check in frappe.get_roles(user)):
        return None  # User has role access, see all
    else:
        # Restrict to assigned/created by user
        return """(`tabToDo`.allocated_to = {user} or `tabToDo`.assigned_by = {user})""".format(
            user=frappe.db.escape(user)
        )
```

### Permission Check Implementation

```python
def has_permission(doc, ptype="read", user=None):
    """Check if user can access specific ToDo"""
    user = user or frappe.session.user
    
    # Check role permissions
    todo_roles = frappe.permissions.get_doctype_roles("ToDo", ptype)
    todo_roles = set(todo_roles) - set(AUTOMATIC_ROLES)
    
    if any(check in todo_roles for check in frappe.get_roles(user)):
        return True
    else:
        # Check if user is allocated_to or assigned_by
        return doc.allocated_to == user or doc.assigned_by == user
```

### Checking Permissions Programmatically

```python
# Check if user can read ToDo
can_read = frappe.has_permission("ToDo", "read", doc="TODO-0001", user="user@example.com")

# Get all accessible ToDo for user
frappe.set_user("user@example.com")
todos = frappe.get_all("ToDo", filters={"status": "Open"})
# Returns only ToDo where user is allocated_to, assigned_by, or has role permission
```

### Permission Scenarios

**Scenario 1: Manager with ToDo role**
```python
# User has "ToDo User" role
# Can see all ToDo documents
frappe.get_all("ToDo")  # Returns all ToDo
```

**Scenario 2: Regular user without role**
```python
# User doesn't have ToDo role
# Can only see their assigned or created ToDo
frappe.get_all("ToDo")  # Returns only relevant ToDo
```

**Scenario 3: Administrator**
```python
# Administrator bypasses all checks
frappe.set_user("Administrator")
frappe.get_all("ToDo")  # Returns all ToDo
```

## Lifecycle and Hooks

### on_update Hook

```python
def on_update(self):
    # Add comment to reference document
    if self._assignment:
        self.add_assign_comment(**self._assignment)
    
    # Update _assign field on reference
    self.update_in_reference()
```

### validate Hook

```python
def validate(self):
    # Prepare assignment message for new ToDo
    if self.is_new():
        if self.assigned_by == self.allocated_to:
            message = "{0} self assigned this task: {1}".format(
                get_fullname(self.assigned_by), 
                self.description
            )
        else:
            message = "{0} assigned {1}: {2}".format(
                get_fullname(self.assigned_by),
                get_fullname(self.allocated_to),
                self.description
            )
        self._assignment = {"text": message, "comment_type": "Assigned"}
    
    # Prepare removal message for status change
    else:
        if self.get_db_value("status") != self.status:
            if self.allocated_to == frappe.session.user:
                message = "{0} removed their assignment.".format(
                    get_fullname(frappe.session.user)
                )
            else:
                message = "Assignment of {0} removed by {1}".format(
                    get_fullname(self.allocated_to),
                    get_fullname(frappe.session.user)
                )
            self._assignment = {"text": message, "comment_type": "Assignment Completed"}
```

### on_trash Hook

```python
def on_trash(self):
    # Delete communication links
    self.delete_communication_links()
    
    # Update _assign field on reference
    self.update_in_reference()
```

### Comment Creation

```python
def add_assign_comment(self, text, comment_type):
    """Add comment to reference document"""
    if not (self.reference_type and self.reference_name):
        return
    
    frappe.get_doc(self.reference_type, self.reference_name).add_comment(
        comment_type, text
    )
```

### Reference Document Update

```python
def update_in_reference(self):
    """Update _assign field on reference document"""
    if not (self.reference_type and self.reference_name):
        return
    
    # Get all open assignments
    assignments = frappe.db.get_values("ToDo",
        {
            "reference_type": self.reference_type,
            "reference_name": str(self.reference_name),
            "status": ("not in", ("Cancelled", "Closed")),
            "allocated_to": ("is", "set")
        },
        "allocated_to",
        pluck=True
    )
    
    # Update _assign field with JSON list
    frappe.db.set_value(
        self.reference_type,
        self.reference_name,
        "_assign",
        json.dumps(assignments) if assignments else "",
        update_modified=False
    )
```

## Best Practices

### 1. Clear Descriptions

```python
# Bad
"Task"

# Good
"Review and approve Sales Order SO-0001 for $50,000"

# Better with HTML
"""<div>
    <p><strong>Action Required:</strong> Review Sales Order</p>
    <ul>
        <li>Order: SO-0001</li>
        <li>Customer: ABC Corp</li>
        <li>Amount: $50,000</li>
    </ul>
</div>"""
```

### 2. Set Realistic Due Dates

```python
# Don't hardcode dates
todo.date = "2024-01-01"  # Bad

# Use dynamic dates
from frappe.utils import add_days, today
todo.date = add_days(today(), 7)  # Good
```

### 3. Use Priorities Consistently

```python
# Define clear criteria
priority_map = {
    "Critical": "High",      # Urgent, blocking
    "Important": "High",     # Important, not urgent
    "Normal": "Medium",      # Standard work
    "Low": "Low"            # Nice to have
}

todo.priority = priority_map.get(issue.severity, "Medium")
```

### 4. Clean Up Completed Todos

```python
# Close instead of leaving open
from frappe.desk.form import assign_to
assign_to.close(doctype, name, user)

# Or via bulk cleanup
def cleanup_old_todos():
    """Close todos for completed documents"""
    completed = frappe.get_all("Issue",
        filters={"status": "Closed"},
        pluck="name"
    )
    
    for issue in completed:
        assign_to.close_all_assignments("Issue", issue, ignore_permissions=True)
```

### 5. Avoid Orphaned Todos

```python
# When deleting documents, clear assignments first
def before_delete(doc):
    from frappe.desk.form import assign_to
    assign_to.clear(doc.doctype, doc.name, ignore_permissions=True)
```

### 6. Query Efficiently

```python
# Bad - loads all fields for all todos
todos = frappe.get_all("ToDo", filters={"status": "Open"})

# Good - specific fields and limits
todos = frappe.get_all("ToDo",
    filters={"status": "Open", "allocated_to": user},
    fields=["name", "description", "date", "priority"],
    order_by="date asc",
    limit=50
)
```

### 7. Handle Notifications

```python
# Let assign_to module handle notifications
from frappe.desk.form import assign_to
assign_to.add({...})  # Sends notification automatically

# Suppress for bulk operations
frappe.flags.mute_emails = True
for doc in docs:
    assign_to.add({...})
frappe.flags.mute_emails = False
```

### 8. Use Assignment Rules When Possible

```python
# Instead of manual assignment in code
def on_submit(doc):
    assign_to.add({
        "assign_to": [get_approver(doc)],
        "doctype": doc.doctype,
        "name": doc.name
    })

# Prefer Assignment Rule
# Configure via UI, easier to maintain
```

### 9. Track Assignment History

```python
# ToDo maintains history via status
# Query past assignments
past_todos = frappe.get_all("ToDo",
    filters={
        "reference_type": "Issue",
        "reference_name": "ISS-001",
        "status": ["in", ["Closed", "Cancelled"]]
    },
    fields=["allocated_to", "status", "modified"],
    order_by="modified desc"
)
```

### 10. Test Permissions

```python
# Always test with non-admin users
frappe.set_user("testuser@example.com")
try:
    todo = frappe.get_doc("ToDo", "TODO-0001")
    print("Access granted")
except frappe.PermissionError:
    print("Access denied")
```
