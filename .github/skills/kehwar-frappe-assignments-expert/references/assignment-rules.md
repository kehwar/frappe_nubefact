# Assignment Rules Reference

Complete guide to configuring and using Assignment Rules for automated document assignment.

## Table of Contents

1. [Assignment Rule Structure](#assignment-rule-structure)
2. [Rule Types](#rule-types)
3. [Conditions](#conditions)
4. [Assignment Days](#assignment-days)
5. [Due Date Management](#due-date-management)
6. [Priority and Multiple Rules](#priority-and-multiple-rules)
7. [Configuration Examples](#configuration-examples)

## Assignment Rule Structure

### Core Fields

```python
{
    "doctype": "Assignment Rule",
    "name": "Rule Name",                    # Unique identifier
    "document_type": "Issue",               # DocType to monitor
    "priority": 0,                          # Higher = runs first
    "disabled": 0,                          # 0=active, 1=disabled
    "description": "Rule description",      # Template support: {{field}}
    
    # Conditions
    "assign_condition": "status == 'Open'", # When to assign
    "unassign_condition": "status == 'Closed'", # When to remove
    "close_condition": "priority == 'Low'", # When to close (optional)
    
    # Assignment strategy
    "rule": "Round Robin",                  # Round Robin | Load Balancing | Based on Field
    "field": None,                          # Required for "Based on Field"
    
    # Users
    "users": [
        {"user": "user1@example.com"},
        {"user": "user2@example.com"}
    ],
    
    # Optional
    "due_date_based_on": "expected_end_date", # Field for due date
    "assignment_days": [                    # Restrict by weekday
        {"day": "Monday"},
        {"day": "Tuesday"}
    ],
    "last_user": "user1@example.com"        # Internal tracking for Round Robin
}
```

### Field Descriptions

- **document_type**: DocType to apply rule to (required)
- **priority**: Integer, higher priority rules evaluated first (default: 0)
- **disabled**: Checkbox to temporarily disable rule
- **description**: Small Text, supports Jinja templates with document fields
- **assign_condition**: Python expression, must evaluate to True to assign (required)
- **unassign_condition**: Python expression, removes assignment when True
- **close_condition**: Python expression, closes (not cancels) assignment when True
- **rule**: Select from Round Robin, Load Balancing, or Based on Field (required)
- **field**: Link to field, used only when rule is "Based on Field"
- **users**: Table of users for assignment pool (required for Round Robin/Load Balancing)
- **due_date_based_on**: Field to use as ToDo due date
- **assignment_days**: Table of weekdays when rule is active
- **last_user**: Link to User, tracks last assigned user for Round Robin

## Rule Types

### 1. Round Robin

Distributes assignments sequentially across users.

**How it works:**
1. Maintains `last_user` field
2. Assigns to next user in list after `last_user`
3. Loops back to first user after reaching end
4. Updates `last_user` after each assignment

**Example:**
```python
assignment_rule = frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Support Ticket Round Robin",
    "document_type": "Issue",
    "assign_condition": "status == 'Open' and priority in ('Medium', 'High')",
    "rule": "Round Robin",
    "users": [
        {"user": "support1@example.com"},
        {"user": "support2@example.com"},
        {"user": "support3@example.com"}
    ]
})
assignment_rule.insert()
```

**Best for:**
- Equal distribution of work over time
- Fair workload sharing
- Simple rotation schemes

### 2. Load Balancing

Assigns to user with least open ToDo items for the DocType.

**How it works:**
1. Queries open ToDo count per user
2. Sorts users by count (ascending)
3. Assigns to user with minimum count
4. Checks only ToDo with matching reference_type

**Example:**
```python
assignment_rule = frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Support Load Balancing",
    "document_type": "Issue",
    "assign_condition": "priority == 'High'",
    "rule": "Load Balancing",
    "users": [
        {"user": "support1@example.com"},
        {"user": "support2@example.com"},
        {"user": "support3@example.com"}
    ]
})
assignment_rule.insert()
```

**Best for:**
- Uneven processing speeds
- Users joining/leaving team
- Ensuring balanced current workload

**Performance note:** Queries database for each assignment, may be slower than Round Robin for high-volume scenarios.

### 3. Based on Field

Assigns to user specified in a document field.

**How it works:**
1. Reads value from specified field
2. Checks if value is a valid User
3. Assigns to that user
4. Skips if field empty or invalid

**Example:**
```python
assignment_rule = frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Assign to Territory Manager",
    "document_type": "Lead",
    "assign_condition": "status == 'Open'",
    "rule": "Based on Field",
    "field": "territory_manager"  # Field must contain user email
})
assignment_rule.insert()
```

**Best for:**
- Hierarchical assignments
- Pre-determined ownership
- Self-assignment workflows

**Requirements:**
- Field must be Link to User or contain user email
- User must exist and be enabled

## Conditions

Conditions are Python expressions evaluated in document context.

### Assign Condition

**Required**. When to create assignment.

**Available context:**
- All document fields directly accessible
- `doc` variable contains document dict

**Examples:**
```python
# Simple field check
"status == 'Open'"

# Multiple conditions
"status == 'Open' and priority == 'High'"

# Field in list
"status in ('Open', 'Working')"

# Numeric comparison
"amount > 10000"

# Date comparison
"due_date < frappe.utils.today()"

# Field existence
"customer and region == 'North'"

# Complex logic
"(priority == 'High' and amount > 5000) or (priority == 'Critical')"
```

### Unassign Condition

**Optional**. When to cancel assignment.

**Behavior:**
- Checks on each document save
- Sets ToDo status to "Cancelled"
- Clears `_assign` field on document

**Examples:**
```python
# Status change
"status in ('Closed', 'Resolved', 'Cancelled')"

# Ownership change
"assigned_to != allocated_to"

# Condition no longer met
"priority == 'Low' or status == 'On Hold'"

# Field cleared
"not sales_person"
```

### Close Condition

**Optional**. When to close (complete) assignment.

**Behavior:**
- Checks on each document save
- Sets ToDo status to "Closed" (not Cancelled)
- Retains assignment history
- Sends completion notification

**Difference from Unassign:**
- Close: Task completed successfully
- Unassign: Task no longer valid/needed

**Examples:**
```python
# Task completed
"status == 'Completed'"

# Approval received
"workflow_state == 'Approved'"

# Specific text in field
'"Closed" in content'

# Multiple completion states
"status in ('Completed', 'Verified', 'Approved')"
```

### Safe Evaluation

Conditions use `frappe.safe_eval()` with limited scope:
- Document fields available
- `frappe.utils` functions available
- File system access blocked
- Import statements blocked

**Available functions:**
```python
frappe.utils.today()
frappe.utils.now()
frappe.utils.nowdate()
frappe.utils.get_datetime()
frappe.utils.add_to_date()
```

**Not available:**
- Database queries (`frappe.db`)
- Session info (`frappe.session`)
- Document operations (`frappe.get_doc`)

## Assignment Days

Restrict rule to specific weekdays.

### Configuration

```python
"assignment_days": [
    {"day": "Monday"},
    {"day": "Tuesday"},
    {"day": "Wednesday"},
    {"day": "Thursday"},
    {"day": "Friday"}
]
```

### Valid Day Values
- Sunday
- Monday
- Tuesday
- Wednesday
- Thursday
- Friday
- Saturday

### Behavior

- If no days specified: Rule active all days
- If days specified: Rule only runs on those days
- Evaluated using `frappe.utils.get_weekday()`
- Respects server timezone

### Example: Business Days Only

```python
assignment_rule = frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Business Hours Support",
    "document_type": "Issue",
    "assign_condition": "priority == 'Medium'",
    "rule": "Round Robin",
    "assignment_days": [
        {"day": "Monday"},
        {"day": "Tuesday"},
        {"day": "Wednesday"},
        {"day": "Thursday"},
        {"day": "Friday"}
    ],
    "users": [{"user": "support@example.com"}]
})
assignment_rule.insert()
```

### Example: Weekend Escalation

```python
assignment_rule = frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Weekend Critical Issues",
    "document_type": "Issue",
    "assign_condition": "priority == 'Critical'",
    "rule": "Round Robin",
    "assignment_days": [
        {"day": "Saturday"},
        {"day": "Sunday"}
    ],
    "users": [
        {"user": "oncall1@example.com"},
        {"user": "oncall2@example.com"}
    ]
})
assignment_rule.insert()
```

## Due Date Management

Automatically set ToDo due dates from document field.

### Configuration

```python
{
    "due_date_based_on": "expected_end_date"  # Field name
}
```

### Behavior

1. ToDo created with date from specified field
2. Monitors field changes
3. Updates open ToDo dates when field changes
4. Only updates ToDo created by this rule

### Example

```python
assignment_rule = frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Project Tasks with Deadline",
    "document_type": "Task",
    "assign_condition": "status == 'Open'",
    "rule": "Load Balancing",
    "due_date_based_on": "expected_end_date",
    "users": [
        {"user": "dev1@example.com"},
        {"user": "dev2@example.com"}
    ]
})
assignment_rule.insert()
```

### Update Behavior

```python
# Create task
task = frappe.get_doc({
    "doctype": "Task",
    "subject": "Fix bug",
    "status": "Open",
    "expected_end_date": "2024-02-01"
}).insert()
# ToDo created with date = "2024-02-01"

# Update task
task.expected_end_date = "2024-02-05"
task.save()
# ToDo date updated to "2024-02-05"
```

### Requirements

- Field must be Date or Datetime type
- Field must exist on DocType
- Only updates open ToDo (status = "Open")

## Priority and Multiple Rules

Multiple rules can apply to same DocType.

### Priority Evaluation

- Rules sorted by priority (descending)
- Higher priority = runs first
- Default priority = 0

### Execution Flow

```
1. Sort rules by priority (high to low)
2. For each rule:
   a. Check if assignment_days match (if specified)
   b. Check unassign_condition on existing assignments
   c. If no assignments remain, check assign_condition
   d. If assign_condition true, assign and stop
3. Check close_condition on remaining assignments
```

### Example: Tiered Assignment

```python
# Priority 2 - Critical issues to senior team
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Critical Issues",
    "document_type": "Issue",
    "priority": 2,
    "assign_condition": "priority == 'Critical'",
    "rule": "Round Robin",
    "users": [
        {"user": "senior1@example.com"},
        {"user": "senior2@example.com"}
    ]
}).insert()

# Priority 1 - High priority to regular team
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "High Priority Issues",
    "document_type": "Issue",
    "priority": 1,
    "assign_condition": "priority == 'High'",
    "rule": "Load Balancing",
    "users": [
        {"user": "support1@example.com"},
        {"user": "support2@example.com"}
    ]
}).insert()

# Priority 0 - Everything else
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Standard Issues",
    "document_type": "Issue",
    "priority": 0,
    "assign_condition": "status == 'Open'",
    "rule": "Round Robin",
    "users": [
        {"user": "junior1@example.com"},
        {"user": "junior2@example.com"}
    ]
}).insert()
```

### Best Practices

1. **Non-overlapping conditions**: Avoid multiple rules matching same document
2. **Clear priorities**: Use meaningful priority gaps (0, 10, 20)
3. **Specific first**: Higher priority for specific conditions
4. **Catch-all last**: Lowest priority for general conditions
5. **Test interactions**: Verify rules work together correctly

## Configuration Examples

### Example 1: Customer Support Tickets

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Support Ticket Assignment",
    "document_type": "Issue",
    "description": "New ticket: {{subject}}",
    "assign_condition": "status == 'Open' and issue_type == 'Support'",
    "unassign_condition": "status in ('Closed', 'Resolved')",
    "rule": "Load Balancing",
    "users": [
        {"user": "support1@example.com"},
        {"user": "support2@example.com"},
        {"user": "support3@example.com"}
    ]
}).insert()
```

### Example 2: Regional Sales Leads

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "North Region Leads",
    "document_type": "Lead",
    "description": "New lead from {{company_name}}",
    "assign_condition": "status == 'Open' and territory == 'North'",
    "rule": "Round Robin",
    "users": [
        {"user": "sales.north1@example.com"},
        {"user": "sales.north2@example.com"}
    ]
}).insert()
```

### Example 3: High-Value Approvals

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Large Order Approvals",
    "document_type": "Sales Order",
    "description": "Order {{name}} requires approval ({{grand_total}})",
    "priority": 10,
    "assign_condition": "docstatus == 0 and grand_total > 100000",
    "close_condition": "docstatus == 1",
    "unassign_condition": "docstatus == 2",
    "rule": "Based on Field",
    "field": "sales_manager",
    "due_date_based_on": "delivery_date"
}).insert()
```

### Example 4: Time-Sensitive Tasks

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Urgent Tasks",
    "document_type": "Task",
    "description": "Urgent: {{subject}}",
    "priority": 5,
    "assign_condition": "status == 'Open' and priority == 'Urgent'",
    "rule": "Load Balancing",
    "due_date_based_on": "exp_end_date",
    "users": [
        {"user": "dev1@example.com"},
        {"user": "dev2@example.com"}
    ]
}).insert()
```

### Example 5: Escalation After Delay

```python
# Regular assignment
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "New Issues",
    "document_type": "Issue",
    "priority": 0,
    "assign_condition": "status == 'Open' and first_response_time is None",
    "rule": "Round Robin",
    "users": [
        {"user": "support1@example.com"},
        {"user": "support2@example.com"}
    ]
}).insert()

# Escalation (handled via scheduled job or workflow)
# Note: Assignment rules don't support time-based conditions directly
# Implement via server script or custom hook
```

### Example 6: Department-Specific Routing

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "HR Department Issues",
    "document_type": "Issue",
    "assign_condition": "department == 'Human Resources' and status == 'Open'",
    "rule": "Round Robin",
    "users": [
        {"user": "hr1@example.com"},
        {"user": "hr2@example.com"}
    ]
}).insert()
```

### Example 7: Self-Assignment

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Assign to Creator",
    "document_type": "Task",
    "description": "Your task: {{subject}}",
    "assign_condition": "status == 'Open'",
    "rule": "Based on Field",
    "field": "owner"  # Auto-assign to document creator
}).insert()
```

### Example 8: Conditional Multi-Stage

```python
# Stage 1: Initial review
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Initial Review",
    "document_type": "Leave Application",
    "priority": 1,
    "assign_condition": "status == 'Open' and leave_approver",
    "rule": "Based on Field",
    "field": "leave_approver"
}).insert()

# Stage 2: HR approval for long leaves
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "HR Approval",
    "document_type": "Leave Application",
    "priority": 2,
    "assign_condition": "workflow_state == 'Approved by Manager' and total_leave_days > 5",
    "rule": "Round Robin",
    "users": [
        {"user": "hr1@example.com"},
        {"user": "hr2@example.com"}
    ]
}).insert()
```

### Example 9: Business Hours Only

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Weekday Support",
    "document_type": "Issue",
    "assign_condition": "priority in ('Low', 'Medium')",
    "rule": "Load Balancing",
    "assignment_days": [
        {"day": "Monday"},
        {"day": "Tuesday"},
        {"day": "Wednesday"},
        {"day": "Thursday"},
        {"day": "Friday"}
    ],
    "users": [
        {"user": "support@example.com"}
    ]
}).insert()
```

### Example 10: Territory Manager with Fallback

```python
# Primary: Territory manager
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Territory Manager",
    "document_type": "Lead",
    "priority": 1,
    "assign_condition": "status == 'Open' and territory_manager",
    "rule": "Based on Field",
    "field": "territory_manager"
}).insert()

# Fallback: Default team if no territory manager
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Default Lead Assignment",
    "document_type": "Lead",
    "priority": 0,
    "assign_condition": "status == 'Open' and not territory_manager",
    "rule": "Round Robin",
    "users": [
        {"user": "sales1@example.com"},
        {"user": "sales2@example.com"}
    ]
}).insert()
```
