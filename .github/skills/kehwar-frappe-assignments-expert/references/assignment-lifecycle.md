# Assignment Lifecycle Reference

Detailed documentation of the assignment lifecycle, state transitions, and integration points.

## Table of Contents

1. [Lifecycle Overview](#lifecycle-overview)
2. [State Transitions](#state-transitions)
3. [Hook Integration](#hook-integration)
4. [Notification Flow](#notification-flow)
5. [Document Integration](#document-integration)

## Lifecycle Overview

### Complete Assignment Flow

```
Document Event (Create/Update)
    ↓
Assignment Rule Triggered (if configured)
    ↓
Condition Evaluation
    ├─ Assign Condition → Create ToDo
    ├─ Unassign Condition → Cancel ToDo
    └─ Close Condition → Close ToDo
    ↓
User Selection (Round Robin / Load Balancing / Field-Based)
    ↓
ToDo Creation
    ├─ Validate User
    ├─ Check Permissions
    └─ Check for Duplicates
    ↓
Document Sharing (if needed)
    ↓
Document Following (if enabled)
    ↓
Notification Sending
    ├─ Notification Log
    └─ Email Queue
    ↓
User Receives Assignment
    ↓
User Works on Task
    ↓
Completion
    ├─ Manual Close
    ├─ Auto Close (via close_condition)
    └─ Cancel (via unassign_condition)
```

## State Transitions

### ToDo Status States

```
Open → Working → Closed
  ↓              ↓
  → Cancelled ←--
```

### State Definitions

**Open**: Initial state
- Assignment is active
- User should work on task
- Counted in workload calculations
- Visible in user's ToDo list

**Closed**: Completed
- Task successfully completed
- User took action
- Retained in history
- Not counted in workload

**Cancelled**: Removed
- Assignment no longer valid
- Condition no longer met
- Document deleted/changed
- Not counted in workload

### Transition Triggers

**Open → Closed:**
```python
# Manual close by user
assign_to.close(doctype, name, user)

# Auto-close via Assignment Rule
"close_condition": "status == 'Completed'"

# Programmatic close
todo.status = "Closed"
todo.save()
```

**Open → Cancelled:**
```python
# Manual remove
assign_to.remove(doctype, name, user)

# Auto-unassign via Assignment Rule
"unassign_condition": "status in ('Closed', 'Invalid')"

# Clear all
assign_to.clear(doctype, name)

# Programmatic cancel
todo.status = "Cancelled"
todo.save()
```

**Closed/Cancelled → Open:**
```python
# Reopen manually
todo = frappe.get_doc("ToDo", todo_name)
todo.status = "Open"
todo.save()

# Reopen via Assignment Rule
# (Assignment rule can reopen closed todos if conditions change)
```

## Hook Integration

### Assignment Rule Hooks

Assignment rules integrate via document lifecycle hooks configured in `hooks.py`:

```python
# frappe/hooks.py
doc_events = {
    "*": {
        "on_update": [
            "frappe.automation.doctype.assignment_rule.assignment_rule.apply",
            "frappe.automation.doctype.assignment_rule.assignment_rule.update_due_date"
        ]
    }
}
```

### Hook Execution Points

**on_update**: After document save
```python
def on_update(doc):
    # Apply assignment rules
    from frappe.automation.doctype.assignment_rule.assignment_rule import apply
    apply(doc)
```

### Rule Application Logic

```python
def apply(doc=None, method=None, doctype=None, name=None):
    # Skip if in installation, patch, etc.
    if frappe.flags.in_patch or frappe.flags.in_install:
        return
    
    # Get active rules for DocType
    assignment_rules = get_doctype_map(
        "Assignment Rule",
        doc.doctype,
        filters={"document_type": doc.doctype, "disabled": 0},
        order_by="priority desc"
    )
    
    # Get existing assignments
    assignments = get_assignments(doc)
    
    # Try to unassign first
    for rule in assignment_rules:
        if rule.is_rule_not_applicable_today():
            continue
        clear = rule.apply_unassign(doc, assignments)
        if clear:
            break
    
    # If all cleared, try to assign
    if clear or not assignments:
        for rule in assignment_rules:
            if rule.is_rule_not_applicable_today():
                continue
            new_apply = rule.apply_assign(doc)
            if new_apply:
                break
    
    # Check close conditions
    for rule in assignment_rules:
        rule.close_assignments(doc)
```

### Custom Controller Hooks

Integrate assignments in custom DocType controllers:

```python
class MyDocType(Document):
    def on_submit(self):
        """Auto-assign on submission"""
        from frappe.desk.form import assign_to
        
        assign_to.add({
            "assign_to": [self.approver],
            "doctype": self.doctype,
            "name": self.name,
            "description": f"Approve {self.name}"
        }, ignore_permissions=True)
    
    def before_cancel(self):
        """Clear assignments before cancellation"""
        from frappe.desk.form import assign_to
        assign_to.clear(
            self.doctype, self.name,
            ignore_permissions=True
        )
    
    def on_trash(self):
        """Clean up assignments on deletion"""
        from frappe.desk.form import assign_to
        assign_to.clear(
            self.doctype, self.name,
            ignore_permissions=True
        )
```

## Notification Flow

### Notification Types and Timing

**Assignment Created:**
```
assign_to.add() called
    ↓
ToDo created
    ↓
notify_assignment(action="ASSIGN")
    ↓
Notification Log created
    ↓
Email enqueued
    ↓
User receives notification
```

**Assignment Removed:**
```
assign_to.remove() called
    ↓
ToDo status → Cancelled
    ↓
notify_assignment(action="CLOSE")
    ↓
Notification Log created
    ↓
User receives notification
```

**Assignment Completed:**
```
assign_to.close() called
    ↓
ToDo status → Closed
    ↓
notify_assignment(action="CLOSE")
    ↓
Notification to assigner
    ↓
Email sent
```

### Notification Content

**Assignment Email:**
```
Subject: {Assigner} assigned a new task {DocType} {Title} to you

Body:
{Description HTML}

[View Document]
[View ToDo]
```

**Removal Email:**
```
Subject: Your assignment on {DocType} {Title} has been removed by {User}

Body:
The assignment has been cancelled.

[View Document]
```

**Completion Notification:**
```
Subject: Assignment completed on {DocType} {Title}

Body:
{User} has completed the task.

[View Document]
```

### Notification Suppression

```python
# Suppress all emails
frappe.flags.mute_emails = True
assign_to.add({...})
frappe.flags.mute_emails = False

# Suppress in tests
frappe.flags.in_test = True
assign_to.add({...})
frappe.flags.in_test = False

# Skip if self-assigned
# (automatically handled in notify_assignment function)
```

### Notification Settings

User-level notification preferences:
- Email notifications enabled/disabled
- Follow assigned documents (auto-follow)
- Notification frequency
- Email digest settings

## Document Integration

### _assign Field

All documents have a virtual `_assign` field that stores assignment information.

**Structure:**
```python
doc._assign = '["user1@example.com", "user2@example.com"]'
```

**Updates:**
```python
# Automatically updated on ToDo changes
def update_in_reference(todo):
    assignments = frappe.db.get_values("ToDo",
        {
            "reference_type": todo.reference_type,
            "reference_name": todo.reference_name,
            "status": ("not in", ("Cancelled", "Closed")),
            "allocated_to": ("is", "set")
        },
        "allocated_to",
        pluck=True
    )
    
    frappe.db.set_value(
        todo.reference_type,
        todo.reference_name,
        "_assign",
        json.dumps(assignments) if assignments else "",
        update_modified=False
    )
```

**Usage:**
```python
# Check if document is assigned
doc = frappe.get_doc("Issue", "ISS-001")
if doc._assign:
    assignees = json.loads(doc._assign)
    print(f"Assigned to: {', '.join(assignees)}")

# Filter assigned documents
assigned_issues = frappe.get_all("Issue",
    filters={
        "_assign": ["like", f"%{frappe.session.user}%"]
    }
)
```

### assigned_to Field

Some DocTypes have an `assigned_to` field for single assignment tracking.

**Auto-update:**
```python
# Set by assign_to.add()
if frappe.get_meta(args["doctype"]).get_field("assigned_to"):
    frappe.db.set_value(
        args["doctype"], 
        args["name"], 
        "assigned_to", 
        assign_to
    )

# Cleared by assign_to.remove() or close()
if frappe.get_meta(doctype).get_field("assigned_to"):
    frappe.db.set_value(doctype, name, "assigned_to", None)
```

**Usage:**
```python
# Define in DocType JSON
{
    "fieldname": "assigned_to",
    "fieldtype": "Link",
    "options": "User",
    "label": "Assigned To"
}

# Query by assigned user
my_issues = frappe.get_all("Issue",
    filters={"assigned_to": frappe.session.user}
)
```

### Timeline Comments

Assignments create timeline comments on reference documents.

**Comment Types:**
```python
# New assignment
"Assigned"
# Message: "{Assigner} assigned {Assignee}: {Description}"

# Assignment removed/completed
"Assignment Completed"
# Message: "{User} removed their assignment" or
#          "Assignment of {User} removed by {Remover}"
```

**Implementation:**
```python
def add_assign_comment(todo, text, comment_type):
    if not (todo.reference_type and todo.reference_name):
        return
    
    frappe.get_doc(
        todo.reference_type,
        todo.reference_name
    ).add_comment(comment_type, text)
```

**Querying Comments:**
```python
comments = frappe.get_all("Comment",
    filters={
        "reference_doctype": "Issue",
        "reference_name": "ISS-001",
        "comment_type": ["in", ["Assigned", "Assignment Completed"]]
    },
    fields=["content", "owner", "creation"],
    order_by="creation desc"
)
```

### Document Sharing

When assignee lacks permission, document is shared automatically.

**Share Logic:**
```python
# Check permission
if not frappe.has_permission(doc=doc, user=assign_to):
    # Check if sharing disabled
    if frappe.get_system_settings("disable_document_sharing"):
        frappe.throw("User not permitted and sharing is disabled")
    else:
        # Share with read access
        frappe.share.add(
            doc.doctype,
            doc.name,
            assign_to,
            read=1,
            write=0
        )
```

**Share Permissions:**
```python
# Default share for assignments
{
    "read": 1,
    "write": 0,
    "submit": 0,
    "share": 0
}

# Custom share
frappe.share.add(
    "Issue", "ISS-001", "user@example.com",
    read=1, write=1, submit=0, share=0
)
```

### Document Following

Users with "Follow Assigned Documents" setting auto-follow.

**Follow Logic:**
```python
if frappe.get_cached_value("User", assign_to, "follow_assigned_documents"):
    from frappe.desk.form.document_follow import follow_document
    follow_document(doctype, name, assign_to)
```

**Follow Notifications:**
- User receives updates on document changes
- Comments, status changes, etc.
- Separate from assignment notifications

**Manage Follows:**
```python
# Follow document
from frappe.desk.form.document_follow import follow_document
follow_document("Issue", "ISS-001", "user@example.com")

# Unfollow
from frappe.desk.form.document_follow import unfollow_document
unfollow_document("Issue", "ISS-001", "user@example.com")
```

## Integration Examples

### Example 1: Approval Workflow

```python
class PurchaseOrder(Document):
    def on_submit(self):
        """Assign for approval after submission"""
        from frappe.desk.form import assign_to
        
        approver = self.get_approver_based_on_amount()
        
        assign_to.add({
            "assign_to": [approver],
            "doctype": self.doctype,
            "name": self.name,
            "description": f"Approve Purchase Order {self.name} worth {self.grand_total}",
            "priority": "High" if self.grand_total > 100000 else "Medium",
            "date": frappe.utils.add_days(frappe.utils.today(), 2)
        }, ignore_permissions=True)
    
    def on_update_after_submit(self):
        """Close assignment when approved"""
        from frappe.desk.form import assign_to
        
        if self.workflow_state == "Approved":
            assign_to.close_all_assignments(
                self.doctype, self.name,
                ignore_permissions=True
            )
    
    def get_approver_based_on_amount(self):
        if self.grand_total > 100000:
            return "cfo@example.com"
        elif self.grand_total > 50000:
            return "finance.manager@example.com"
        else:
            return "accountant@example.com"
```

### Example 2: Escalation System

```python
def escalate_overdue_assignments():
    """Scheduled job to escalate overdue assignments"""
    from frappe.utils import today, add_days, get_datetime
    from frappe.desk.form import assign_to
    
    # Find overdue todos (>2 days old)
    overdue_date = add_days(today(), -2)
    
    overdue_todos = frappe.get_all("ToDo",
        filters={
            "status": "Open",
            "date": ["<", overdue_date]
        },
        fields=["name", "allocated_to", "reference_type", "reference_name", "description"]
    )
    
    for todo in overdue_todos:
        # Get manager
        manager = frappe.db.get_value("User", todo.allocated_to, "manager")
        
        if manager:
            # Assign to manager
            assign_to.add({
                "assign_to": [manager],
                "doctype": todo.reference_type,
                "name": todo.reference_name,
                "description": f"ESCALATED: {todo.description}<br>Original assignee: {todo.allocated_to}",
                "priority": "High"
            }, ignore_permissions=True)
            
            # Add comment
            doc = frappe.get_doc(todo.reference_type, todo.reference_name)
            doc.add_comment("Info", f"Assignment escalated to {manager} due to delay")
```

### Example 3: Multi-Stage Assignment

```python
class LeaveApplication(Document):
    def on_update(self):
        """Handle multi-stage approvals"""
        from frappe.desk.form import assign_to
        
        # Stage 1: Manager approval
        if self.workflow_state == "Pending Manager Approval":
            assign_to.add({
                "assign_to": [self.leave_approver],
                "doctype": self.doctype,
                "name": self.name,
                "description": f"Approve leave for {self.employee_name}",
                "priority": "Medium"
            }, ignore_permissions=True)
        
        # Stage 2: HR approval for long leaves
        elif self.workflow_state == "Pending HR Approval":
            # Close manager assignment
            assign_to.close_all_assignments(
                self.doctype, self.name,
                ignore_permissions=True
            )
            
            # Assign to HR
            hr_managers = frappe.get_all("User",
                filters={"role_profile_name": "HR Manager"},
                pluck="name"
            )
            
            if hr_managers:
                assign_to.add({
                    "assign_to": hr_managers,
                    "doctype": self.doctype,
                    "name": self.name,
                    "description": f"HR approval required for {self.total_leave_days} days leave",
                    "priority": "High"
                }, ignore_permissions=True)
        
        # Final approval
        elif self.workflow_state == "Approved":
            assign_to.close_all_assignments(
                self.doctype, self.name,
                ignore_permissions=True
            )
```

### Example 4: SLA-Based Assignment

```python
class SupportTicket(Document):
    def on_update(self):
        """Assign based on SLA priority"""
        from frappe.desk.form import assign_to
        from frappe.utils import add_to_date, now_datetime
        
        if self.has_value_changed("priority") and self.priority == "Critical":
            # Clear existing assignments
            assign_to.clear(self.doctype, self.name, ignore_permissions=True)
            
            # Calculate SLA due date
            sla_hours = {
                "Critical": 1,
                "High": 4,
                "Medium": 24,
                "Low": 48
            }
            
            due_date = add_to_date(
                now_datetime(),
                hours=sla_hours.get(self.priority, 24),
                as_datetime=True
            )
            
            # Assign to senior support
            assign_to.add({
                "assign_to": ["senior.support@example.com"],
                "doctype": self.doctype,
                "name": self.name,
                "description": f"URGENT: {self.subject}<br>SLA: {sla_hours[self.priority]} hours",
                "priority": "High",
                "date": due_date.strftime("%Y-%m-%d")
            }, ignore_permissions=True)
```

### Example 5: Team Assignment with Rotation

```python
def assign_to_team_rotation(doctype, name, team_role):
    """Assign to team using load balancing"""
    from frappe.desk.form import assign_to
    
    # Get team members
    team_members = frappe.get_all("Has Role",
        filters={"role": team_role, "parenttype": "User"},
        fields=["parent as user"]
    )
    
    if not team_members:
        frappe.throw(f"No users found with role {team_role}")
    
    # Get workload for each member
    workload = []
    for member in team_members:
        count = frappe.db.count("ToDo",
            filters={
                "allocated_to": member.user,
                "status": "Open",
                "reference_type": doctype
            }
        )
        workload.append({"user": member.user, "count": count})
    
    # Assign to member with least work
    workload.sort(key=lambda x: x["count"])
    selected_user = workload[0]["user"]
    
    assign_to.add({
        "assign_to": [selected_user],
        "doctype": doctype,
        "name": name,
        "description": f"Assigned to {team_role} team"
    }, ignore_permissions=True)
    
    return selected_user
```
