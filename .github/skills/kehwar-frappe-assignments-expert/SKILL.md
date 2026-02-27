---
name: kehwar-frappe-assignments-expert
description: Expert guidance on Frappe assignments system including Assignment Rules (auto-assignment with round robin, load balancing, and field-based rules), ToDo management (task assignments, status tracking, and operations), and assign_to.py module (programmatic assignment operations). Use when creating or modifying assignment rules, working with ToDo documents, implementing auto-assignment logic, troubleshooting assignment issues, or understanding assignment workflows and notifications.
---

# Frappe Assignments Expert

This skill provides comprehensive guidance for understanding and working with Frappe's assignments system.

## Overview

Frappe's assignments system enables task assignment and tracking through three core components:

1. **Assignment Rules**: Automated assignment of documents to users based on conditions using round robin, load balancing, or field-based strategies
2. **ToDo**: Task management documents that track assignments with status, priority, and due dates
3. **assign_to.py**: Programmatic API for assignment operations like add, remove, close, and clear

## Key Concepts

### Assignment Flow

```
Document Created/Updated
    ↓
Assignment Rule Evaluates (if configured)
    ↓
Condition Matches → ToDo Created
    ↓
User Assigned → Notification Sent
    ↓
User Completes → ToDo Closed
```

### Core Components

**Assignment Rule**: Configuration that automatically assigns documents to users
- **Document Type**: Which DocType to monitor
- **Assign Condition**: When to assign (Python expression)
- **Unassign Condition**: When to remove assignment
- **Close Condition**: When to close assignment
- **Rule Type**: How to select user (Round Robin, Load Balancing, Based on Field)
- **Users**: Pool of users for assignment

**ToDo**: Task assignment record
- **allocated_to**: User assigned to the task
- **assigned_by**: User who created the assignment
- **reference_type/name**: Document being assigned
- **status**: Open, Closed, or Cancelled
- **priority**: High, Medium, or Low
- **date**: Due date

**assign_to.py**: Python module with assignment functions
- `add()`: Create new assignment
- `remove()`: Cancel assignment
- `close()`: Close completed assignment
- `clear()`: Clear all assignments

## Quick Reference

### Creating Assignment Rules

```python
# Via UI: Automation > Assignment Rule
# Or programmatically:
assignment_rule = frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Assign Open Issues",
    "document_type": "Issue",
    "assign_condition": "status == 'Open'",
    "unassign_condition": "status in ('Closed', 'Resolved')",
    "rule": "Round Robin",
    "priority": 0,
    "disabled": 0,
    "users": [
        {"user": "user1@example.com"},
        {"user": "user2@example.com"}
    ]
})
assignment_rule.insert()
```

### Manual Assignment Operations

```python
# Add assignment
from frappe.desk.form import assign_to

assign_to.add({
    "assign_to": ["user@example.com"],
    "doctype": "Issue",
    "name": "ISS-001",
    "description": "Please review this issue",
    "priority": "High",
    "date": "2024-01-31"
})

# Remove assignment
assign_to.remove("Issue", "ISS-001", "user@example.com")

# Close assignment
assign_to.close("Issue", "ISS-001", "user@example.com")

# Clear all assignments
assign_to.clear("Issue", "ISS-001")
```

### Working with ToDo

```python
# Get assignments for a document
todos = frappe.get_all("ToDo",
    filters={
        "reference_type": "Issue",
        "reference_name": "ISS-001",
        "status": "Open"
    }
)

# Create ToDo directly
todo = frappe.get_doc({
    "doctype": "ToDo",
    "allocated_to": "user@example.com",
    "description": "Review document",
    "priority": "Medium",
    "status": "Open"
})
todo.insert()
```

## Assignment Rules

Assignment Rules provide automated document assignment with three strategies:

### Rule Types

**1. Round Robin**: Assigns to users in sequence
- Distributes work evenly over time
- Next user gets assignment each time
- Loops back to first user after last

**2. Load Balancing**: Assigns to user with least open assignments
- Distributes work based on current workload
- Checks open ToDo count per user
- Assigns to user with minimum assignments

**3. Based on Field**: Assigns based on document field value
- Uses a specific field value as assignee
- Field must contain valid user email
- Useful for self-assignment or hierarchical assignment

**When to read:** See [references/assignment-rules.md](references/assignment-rules.md) for complete Assignment Rule configuration with 15+ examples including conditional assignment, multi-level routing, due date management, and scheduling rules.

## ToDo Management

ToDo documents track task assignments with status and lifecycle management.

### ToDo Fields

- **allocated_to**: User assigned (required)
- **assigned_by**: User who created assignment
- **reference_type/name**: Linked document
- **description**: Task details (supports HTML)
- **status**: Open, Closed, Cancelled
- **priority**: High, Medium, Low
- **date**: Due date
- **assignment_rule**: If created by assignment rule

### ToDo Permissions

Users can view ToDo if they are:
- The allocated_to user
- The assigned_by user
- Have role permission for ToDo DocType

**When to read:** See [references/todo-management.md](references/todo-management.md) for ToDo operations with comprehensive examples including querying, creating, updating, and permission handling.

## assign_to.py API

The assign_to module provides functions for programmatic assignment management.

### Main Functions

```python
from frappe.desk.form import assign_to

# Add assignment(s)
assign_to.add(args, ignore_permissions=False)
# args: {"assign_to": [], "doctype": "", "name": "", "description": "", "priority": "", "date": ""}

# Add to multiple documents
assign_to.add_multiple(args)
# args: {"assign_to": [], "doctype": "", "name": ["doc1", "doc2"]}

# Get assignments
assign_to.get(args)
# Returns list of assignments for document

# Remove assignment
assign_to.remove(doctype, name, assign_to, ignore_permissions=False)

# Remove from multiple documents
assign_to.remove_multiple(doctype, names, ignore_permissions=False)

# Close assignment
assign_to.close(doctype, name, assign_to, ignore_permissions=False)

# Close all assignments
assign_to.close_all_assignments(doctype, name, ignore_permissions=False)

# Clear all assignments
assign_to.clear(doctype, name, ignore_permissions=False)
```

**When to read:** See [references/assign-to-api.md](references/assign-to-api.md) for complete API reference with detailed function signatures, parameters, return values, and 20+ usage examples.

## Assignment Lifecycle

### Creation

1. Document matches Assignment Rule condition
2. Rule selects user based on strategy
3. ToDo document created with assignment details
4. If user lacks permission, document is shared
5. If user follows assigned documents, they follow the document
6. Notification sent to assigned user

### Updates

1. Assignment Rule monitors document changes
2. Unassign condition triggers assignment cancellation
3. Close condition triggers assignment closure
4. Due date changes propagate to open ToDo

### Completion

1. User completes task
2. Assignment closed via UI or API
3. Status changed to "Closed"
4. Timeline comment added to document
5. Notification sent to assigner

**When to read:** See [references/assignment-lifecycle.md](references/assignment-lifecycle.md) for detailed lifecycle documentation with state transitions, hooks, and notification flows.

## Notifications

Assignment operations trigger notifications to keep users informed.

### Notification Types

**Assignment Created**: Sent to allocated_to user
- Subject: "{Assigner} assigned a new task {DocType} {Title} to you"
- Includes description and document link
- Email sent if user has email notifications enabled

**Assignment Removed**: Sent to allocated_to user
- Subject: "Your assignment on {DocType} {Title} has been removed by {User}"
- Notifies of cancellation

**Assignment Closed**: Sent to assigned_by user
- Notifies assigner when task is completed
- Shows who completed the task

### Controlling Notifications

```python
# Disable notification for programmatic assignment
frappe.flags.in_test = True  # or
frappe.flags.mute_emails = True

# Add with notification
assign_to.add({...}, notify=True)
```

**When to read:** See [references/notifications.md](references/notifications.md) for notification configuration, customization, and email template details.

## Common Patterns

### Auto-assign to Support Team

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Support Issues",
    "document_type": "Issue",
    "assign_condition": "priority == 'High'",
    "rule": "Load Balancing",
    "users": [
        {"user": "support1@example.com"},
        {"user": "support2@example.com"}
    ]
}).insert()
```

### Assign Based on Territory

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Regional Sales",
    "document_type": "Lead",
    "assign_condition": "status == 'Open'",
    "rule": "Based on Field",
    "field": "territory_manager"
}).insert()
```

### Temporary Manual Assignment

```python
# Quick assignment without rule
assign_to.add({
    "assign_to": ["reviewer@example.com"],
    "doctype": "Sales Order",
    "name": "SO-001",
    "description": "Please approve this order",
    "priority": "High"
})
```

**When to read:** See [references/common-patterns.md](references/common-patterns.md) for 20+ assignment patterns including escalation, hierarchical routing, SLA-based assignment, and conditional workflows.

## Best Practices

### Assignment Rule Design

1. **Keep conditions simple**: Use straightforward Python expressions
2. **Set appropriate priority**: Higher priority rules run first
3. **Test thoroughly**: Verify assignment logic with different scenarios
4. **Use unassign conditions**: Clear assignments when no longer needed
5. **Monitor performance**: Watch for assignment bottlenecks

### ToDo Management

1. **Clear descriptions**: Provide context for assignees
2. **Set realistic due dates**: Avoid overdue assignments
3. **Use priorities**: Mark urgent tasks as High
4. **Close completed tasks**: Keep assignment list clean
5. **Avoid orphaned ToDos**: Clear assignments when documents are deleted

### Performance

1. **Index reference fields**: Ensure ToDo reference fields are indexed
2. **Limit assignment pool**: Don't add unnecessary users to rules
3. **Use assignment days**: Restrict rules to specific weekdays if appropriate
4. **Batch operations**: Use `add_multiple` for bulk assignments
5. **Background processing**: Assignment rules run async for large documents

**When to read:** See [references/best-practices.md](references/best-practices.md) for comprehensive guidelines on security, performance, maintainability, and troubleshooting.

## Debugging Assignments

### Common Issues

**Assignment not created**:
- Check Assignment Rule is enabled
- Verify assign_condition evaluates to True
- Check user exists and is enabled
- Review assignment_days configuration

**Assignment to wrong user**:
- Verify rule type (Round Robin vs Load Balancing)
- Check last_user field value
- Review open ToDo counts per user

**Notifications not sent**:
- Check user has email configured
- Verify email queue is processing
- Check notification settings per user

### Debug Commands

```python
# Check active rules for DocType
from frappe.automation.doctype.assignment_rule.assignment_rule import get_assignment_rules
rules = get_assignment_rules()

# Check assignments for document
todos = frappe.get_all("ToDo",
    filters={"reference_type": "Issue", "reference_name": "ISS-001"},
    fields=["*"]
)

# Test assignment condition
doc = frappe.get_doc("Issue", "ISS-001")
rule = frappe.get_doc("Assignment Rule", "My Rule")
result = frappe.safe_eval(rule.assign_condition, None, doc.as_dict())
```

**When to read:** See [references/debugging.md](references/debugging.md) for comprehensive debugging workflows, logging techniques, and troubleshooting scenarios.

## Testing Assignment Logic

```python
# Test assignment creation
from frappe.tests.utils import FrappeTestCase

class TestAssignments(FrappeTestCase):
    def test_assignment_rule(self):
        # Create test rule
        rule = frappe.get_doc({
            "doctype": "Assignment Rule",
            "document_type": "Issue",
            "assign_condition": "status == 'Open'",
            "rule": "Round Robin",
            "users": [{"user": "test@example.com"}]
        }).insert()

        # Create document
        issue = frappe.get_doc({
            "doctype": "Issue",
            "subject": "Test",
            "status": "Open"
        }).insert()

        # Verify assignment
        todos = frappe.get_all("ToDo",
            filters={"reference_name": issue.name}
        )
        self.assertEqual(len(todos), 1)
```

**When to read:** See [references/testing.md](references/testing.md) for comprehensive testing patterns and unit test examples.

## Core Implementation Files

Key files in Frappe codebase:
- `/frappe/automation/doctype/assignment_rule/assignment_rule.py` - Assignment Rule logic
- `/frappe/desk/form/assign_to.py` - Assignment operations API
- `/frappe/desk/doctype/todo/todo.py` - ToDo DocType controller
- `/frappe/model/workflow.py` - Workflow integration with assignments

## Usage

When working with assignments:

1. **Understand requirements**: What triggers assignment? Who should be assigned?
2. **Choose approach**: Automated (Assignment Rule) vs Manual (assign_to API)
3. **Select strategy**: Round Robin, Load Balancing, or Field-based
4. **Configure conditions**: When to assign, unassign, and close
5. **Test thoroughly**: Verify with different users and scenarios
6. **Monitor performance**: Check for bottlenecks and improve
7. **Document logic**: Add comments explaining assignment rules

## Important Notes

- Assignment Rules run on document save/update via hooks
- Only one assignment per user per document (prevents duplicates)
- Assignments respect document permissions (shares document if needed)
- Assignment Rules cannot assign ToDo DocType (prevents recursion)
- Administrator can see all ToDo documents regardless of assignment
- Assignment days filter rules by weekday (useful for business hours)
- Due dates from Assignment Rules sync with document field changes
- Bulk assignment operations (>5 docs) run in background queue
