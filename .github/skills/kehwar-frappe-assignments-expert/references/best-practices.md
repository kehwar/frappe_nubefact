# Best Practices for Assignments

Comprehensive guidelines for effective assignment system usage.

## Table of Contents

1. [Assignment Rule Design](#assignment-rule-design)
2. [Performance Optimization](#performance-optimization)
3. [Security and Permissions](#security-and-permissions)
4. [Maintainability](#maintainability)
5. [Testing](#testing)
6. [Monitoring and Debugging](#monitoring-and-debugging)

## Assignment Rule Design

### Keep Conditions Simple

**Bad:**
```python
"assign_condition": "(status == 'Open' and (priority == 'High' or priority == 'Critical') and (territory == 'North' or territory == 'South') and amount > 10000 and created_by != 'Administrator' and not is_internal)"
```

**Good:**
```python
# Split into multiple rules with clear priorities
"assign_condition": "status == 'Open' and priority == 'High' and amount > 10000"
```

**Benefits:**
- Easier to understand and maintain
- Simpler debugging
- Better performance
- Clearer business logic

### Use Appropriate Priority Levels

```python
# Use meaningful gaps for easy insertion
PRIORITY_CRITICAL = 100
PRIORITY_HIGH = 50
PRIORITY_MEDIUM = 20
PRIORITY_LOW = 10
PRIORITY_DEFAULT = 0

# Example
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "VIP Customer Leads",
    "priority": PRIORITY_CRITICAL,
    "assign_condition": "customer_type == 'VIP'"
}).insert()
```

### Avoid Overlapping Conditions

**Bad:**
```python
# Rule 1
"assign_condition": "status == 'Open'"

# Rule 2 (overlaps with Rule 1)
"assign_condition": "status == 'Open' and priority == 'High'"
```

**Good:**
```python
# Rule 1 - High priority
"assign_condition": "status == 'Open' and priority == 'High'"
"priority": 10

# Rule 2 - Everything else
"assign_condition": "status == 'Open' and priority != 'High'"
"priority": 0
```

### Set Clear Unassign Conditions

Always define when assignments should be removed:

```python
{
    "assign_condition": "status == 'Open'",
    "unassign_condition": "status in ('Closed', 'Cancelled', 'Resolved')",
    "close_condition": "status == 'Completed'"  # Optional
}
```

### Use Descriptive Names and Descriptions

**Bad:**
```python
{
    "name": "Rule 1",
    "description": "Assignment"
}
```

**Good:**
```python
{
    "name": "High Priority Support Tickets - North Region",
    "description": "Urgent support ticket {{subject}} from {{customer}} in North region"
}
```

### Test Rule Logic Before Deployment

```python
# Test condition evaluation
doc = frappe.get_doc("Issue", "ISS-001")
rule = frappe.get_doc("Assignment Rule", "My Rule")

# Test assign condition
result = frappe.safe_eval(rule.assign_condition, None, doc.as_dict())
print(f"Assign condition: {result}")

# Test unassign condition
result = frappe.safe_eval(rule.unassign_condition, None, doc.as_dict())
print(f"Unassign condition: {result}")
```

## Performance Optimization

### Index Reference Fields

ToDo queries are frequent and should be optimized:

```python
# Already indexed by default
frappe.db.add_index("ToDo", ["reference_type", "reference_name"])
frappe.db.add_index("ToDo", ["allocated_to", "status"])
frappe.db.add_index("ToDo", ["status", "date"])
```

### Use Load Balancing Carefully

Load Balancing queries database for each assignment:

```python
# Each assignment does:
SELECT COUNT(*) FROM `tabToDo`
WHERE reference_type = 'Issue'
  AND allocated_to = 'user@example.com'
  AND status = 'Open'
```

**Optimization:**
- Limit user pool size
- Use Round Robin for high-volume scenarios
- Consider caching workload counts

### Batch Operations

For bulk assignments, use appropriate methods:

**Bad:**
```python
for doc_name in doc_list:
    assign_to.add({
        "assign_to": ["user@example.com"],
        "doctype": "Issue",
        "name": doc_name
    })
```

**Good:**
```python
from frappe.desk.form import assign_to

assign_to.add_multiple({
    "assign_to": ["user@example.com"],
    "doctype": "Issue",
    "name": json.dumps(doc_list)
})

# Or suppress emails for bulk
frappe.flags.mute_emails = True
for doc_name in doc_list:
    assign_to.add({...})
frappe.flags.mute_emails = False
```

### Limit Assignment Days

If rules don't need to run every day, restrict them:

```python
{
    "assignment_days": [
        {"day": "Monday"},
        {"day": "Tuesday"},
        {"day": "Wednesday"},
        {"day": "Thursday"},
        {"day": "Friday"}
    ]
}
```

### Optimize User Pool

Only include active, relevant users:

```python
# Query active users
active_users = frappe.get_all("User",
    filters={
        "enabled": 1,
        "user_type": "System User",
        "name": ["in", ["user1@example.com", "user2@example.com"]]
    }
)

# Verify before adding to rule
users_list = [{"user": u.name} for u in active_users]
```

### Cache Frequently Accessed Data

```python
# Bad - queries database each time
def get_approver(doc):
    return frappe.db.get_value("User", {"role": "Approver"}, "name")

# Good - use cached value
def get_approver(doc):
    return frappe.get_cached_value("User", "approver@example.com", "name")
```

## Security and Permissions

### Always Validate Permissions

```python
# In custom assignment logic
def custom_assign(doctype, name, user):
    from frappe.desk.form import assign_to
    
    # Check if current user can assign
    doc = frappe.get_doc(doctype, name)
    if not frappe.has_permission(doc, "write"):
        frappe.throw("You don't have permission to assign this document")
    
    # Check if target user exists and is enabled
    if not frappe.db.get_value("User", user, "enabled"):
        frappe.throw("Cannot assign to disabled user")
    
    assign_to.add({
        "assign_to": [user],
        "doctype": doctype,
        "name": name
    })
```

### Use ignore_permissions Carefully

Only use `ignore_permissions=True` when necessary:

```python
# Good use cases:
# 1. System-level assignment rules
# 2. Automated workflows
# 3. Background jobs

# Always document why
assign_to.add({...}, ignore_permissions=True)  # Assignment rule automation
```

### Validate User Existence

```python
def safe_assign(doctype, name, users):
    from frappe.desk.form import assign_to
    
    # Validate all users exist
    valid_users = []
    for user in users:
        if frappe.db.exists("User", {"name": user, "enabled": 1}):
            valid_users.append(user)
        else:
            frappe.msgprint(f"User {user} not found or disabled", alert=True)
    
    if valid_users:
        assign_to.add({
            "assign_to": valid_users,
            "doctype": doctype,
            "name": name
        })
```

### Respect Document Sharing Settings

```python
# Check sharing settings
disable_sharing = frappe.get_system_settings("disable_document_sharing")

if disable_sharing:
    # Ensure user has permission before assigning
    if not frappe.has_permission(doctype, "read", user=assign_to_user):
        frappe.throw("User lacks permission and document sharing is disabled")
```

### Sanitize Descriptions

When using user input in descriptions:

```python
from frappe.utils import sanitize_html, strip_html

# Sanitize HTML content
description = sanitize_html(user_input)

# Or strip HTML completely
description = strip_html(user_input)
```

## Maintainability

### Document Business Logic

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "High Value Leads",
    "description": """
        Business Rule: High-value leads (>$50K) are assigned to senior sales team
        for immediate follow-up within 24 hours.
        
        Owner: Sales Manager
        Last Updated: 2024-01-15
        SLA: 24 hours
    """,
    "assign_condition": "status == 'Open' and expected_revenue > 50000"
}).insert()
```

### Use Constants for Magic Values

```python
# constants.py
ISSUE_STATUS_OPEN = "Open"
ISSUE_STATUS_CLOSED = "Closed"
PRIORITY_HIGH = "High"
AMOUNT_THRESHOLD_SENIOR = 50000

# assignment_rules.py
from myapp.constants import *

frappe.get_doc({
    "doctype": "Assignment Rule",
    "assign_condition": f"status == '{ISSUE_STATUS_OPEN}' and priority == '{PRIORITY_HIGH}'"
}).insert()
```

### Centralize Assignment Logic

```python
# Don't scatter assignment logic across multiple files
# Create a dedicated module

# myapp/assignments.py
class AssignmentManager:
    @staticmethod
    def assign_to_territory_manager(doc):
        """Assign lead to territory manager"""
        # ... logic here
    
    @staticmethod
    def assign_to_support_team(doc):
        """Assign issue to support team"""
        # ... logic here
    
    @staticmethod
    def escalate_assignment(doc, level):
        """Escalate assignment to next level"""
        # ... logic here

# Usage
from myapp.assignments import AssignmentManager
AssignmentManager.assign_to_territory_manager(lead)
```

### Version Control Configuration

Track assignment rules in version control:

```python
# Create fixtures for assignment rules
# hooks.py
fixtures = [
    {
        "dt": "Assignment Rule",
        "filters": [
            ["name", "in", [
                "Support Ticket Distribution",
                "High Priority Issues",
                "Regional Sales Leads"
            ]]
        ]
    }
]

# Export
bench --site mysite export-fixtures

# Import
bench --site mysite import-fixtures
```

### Add Comments to Complex Conditions

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Complex Business Rule",
    "description": """
        Assigns orders meeting ALL criteria:
        1. Amount > $10,000
        2. Customer in premium tier
        3. Order placed during business hours
        4. Assigned account manager exists
        
        Rationale: High-value orders need immediate attention
        from dedicated account managers during business hours.
    """,
    "assign_condition": """
        grand_total > 10000 
        and customer_tier == 'Premium'
        and not is_after_hours
        and account_manager
    """
}).insert()
```

## Testing

### Unit Tests for Assignment Logic

```python
from frappe.tests.utils import FrappeTestCase

class TestAssignmentRules(FrappeTestCase):
    def setUp(self):
        """Create test data"""
        self.create_test_users()
        self.create_test_rule()
    
    def tearDown(self):
        """Clean up"""
        frappe.db.delete("Assignment Rule")
        frappe.db.delete("ToDo")
    
    def test_round_robin_assignment(self):
        """Test round robin distributes evenly"""
        # Create 3 issues
        for i in range(3):
            issue = self.create_test_issue()
        
        # Check each user got 1 assignment
        for user in ["user1@test.com", "user2@test.com", "user3@test.com"]:
            count = frappe.db.count("ToDo", {
                "allocated_to": user,
                "status": "Open"
            })
            self.assertEqual(count, 1)
    
    def test_load_balancing_assignment(self):
        """Test load balancing assigns to user with least work"""
        # Pre-assign 2 todos to user1
        for i in range(2):
            self.create_todo("user1@test.com")
        
        # Create new issue (should go to user2 or user3)
        issue = self.create_test_issue()
        
        # Verify user1 didn't get it
        todo = frappe.get_all("ToDo",
            filters={"reference_name": issue.name},
            pluck="allocated_to"
        )[0]
        self.assertNotEqual(todo, "user1@test.com")
    
    def test_unassign_condition(self):
        """Test unassign removes assignments"""
        issue = self.create_test_issue(status="Open")
        
        # Verify assignment created
        todos = frappe.get_all("ToDo", {
            "reference_name": issue.name,
            "status": "Open"
        })
        self.assertEqual(len(todos), 1)
        
        # Close issue
        issue.status = "Closed"
        issue.save()
        
        # Verify assignment cancelled
        todos = frappe.get_all("ToDo", {
            "reference_name": issue.name,
            "status": "Open"
        })
        self.assertEqual(len(todos), 0)
    
    def test_permission_sharing(self):
        """Test document shared when user lacks permission"""
        # Create issue as admin
        frappe.set_user("Administrator")
        issue = self.create_test_issue()
        
        # Assign to user without permission
        from frappe.desk.form import assign_to
        assign_to.add({
            "assign_to": ["limited_user@test.com"],
            "doctype": "Issue",
            "name": issue.name
        })
        
        # Verify document was shared
        share = frappe.db.exists("DocShare", {
            "share_doctype": "Issue",
            "share_name": issue.name,
            "user": "limited_user@test.com"
        })
        self.assertTrue(share)
```

### Integration Tests

```python
def test_assignment_workflow_integration():
    """Test assignment with workflow"""
    # Create purchase order
    po = frappe.get_doc({
        "doctype": "Purchase Order",
        "supplier": "Test Supplier",
        "grand_total": 75000
    }).insert()
    
    # Submit (should trigger assignment)
    po.submit()
    
    # Verify assignment to finance manager
    todos = frappe.get_all("ToDo",
        filters={"reference_name": po.name},
        pluck="allocated_to"
    )
    self.assertIn("finance.manager@test.com", todos)
    
    # Approve (should close assignment)
    po.workflow_state = "Approved"
    po.save()
    
    # Verify assignment closed
    todos = frappe.get_all("ToDo",
        filters={
            "reference_name": po.name,
            "status": "Closed"
        }
    )
    self.assertEqual(len(todos), 1)
```

### Performance Tests

```python
def test_assignment_performance():
    """Test assignment performance under load"""
    import time
    
    start = time.time()
    
    # Create 100 assignments
    for i in range(100):
        issue = create_test_issue()
    
    duration = time.time() - start
    
    # Should complete in reasonable time
    assert duration < 30, f"Assignment took {duration}s for 100 docs"
    
    # Verify all assigned
    count = frappe.db.count("ToDo", {"status": "Open"})
    assert count == 100
```

## Monitoring and Debugging

### Enable Debug Logging

```python
# In development
frappe.conf.developer_mode = 1

# In code
import logging
logger = logging.getLogger(__name__)

def apply_assignment(doc):
    logger.debug(f"Applying assignment rules to {doc.doctype} {doc.name}")
    # ... assignment logic
    logger.debug(f"Assignment completed for {doc.name}")
```

### Monitor Assignment Metrics

```python
def get_assignment_metrics():
    """Get assignment system metrics"""
    return {
        "open_assignments": frappe.db.count("ToDo", {"status": "Open"}),
        "closed_today": frappe.db.count("ToDo", {
            "status": "Closed",
            "modified": [">=", frappe.utils.today()]
        }),
        "overdue": frappe.db.count("ToDo", {
            "status": "Open",
            "date": ["<", frappe.utils.today()]
        }),
        "active_rules": frappe.db.count("Assignment Rule", {"disabled": 0})
    }
```

### Create Assignment Dashboard

```python
@frappe.whitelist()
def get_assignment_dashboard():
    """Dashboard data for assignments"""
    # By user
    by_user = frappe.db.sql("""
        SELECT allocated_to, COUNT(*) as count
        FROM `tabToDo`
        WHERE status = 'Open'
        GROUP BY allocated_to
        ORDER BY count DESC
        LIMIT 10
    """, as_dict=True)
    
    # By doctype
    by_doctype = frappe.db.sql("""
        SELECT reference_type, COUNT(*) as count
        FROM `tabToDo`
        WHERE status = 'Open' AND reference_type IS NOT NULL
        GROUP BY reference_type
    """, as_dict=True)
    
    # Overdue
    overdue = frappe.db.sql("""
        SELECT allocated_to, COUNT(*) as count
        FROM `tabToDo`
        WHERE status = 'Open' AND date < CURDATE()
        GROUP BY allocated_to
    """, as_dict=True)
    
    return {
        "by_user": by_user,
        "by_doctype": by_doctype,
        "overdue": overdue
    }
```

### Alert on Assignment Issues

```python
def check_assignment_health():
    """Scheduled job to check assignment health"""
    issues = []
    
    # Check for disabled rules
    disabled_rules = frappe.get_all("Assignment Rule",
        filters={"disabled": 1}
    )
    if disabled_rules:
        issues.append(f"{len(disabled_rules)} assignment rules are disabled")
    
    # Check for overdue assignments
    overdue_count = frappe.db.count("ToDo", {
        "status": "Open",
        "date": ["<", frappe.utils.add_days(frappe.utils.today(), -7)]
    })
    if overdue_count > 10:
        issues.append(f"{overdue_count} assignments overdue by >7 days")
    
    # Check for stuck assignments
    stuck = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabToDo`
        WHERE status = 'Open'
        AND modified < DATE_SUB(NOW(), INTERVAL 30 DAY)
    """)[0][0]
    if stuck > 0:
        issues.append(f"{stuck} assignments not updated in 30 days")
    
    # Send alert if issues found
    if issues:
        send_alert("Assignment System Health Check", "\n".join(issues))
```

### Audit Trail

```python
def log_assignment_change(todo, action):
    """Log assignment changes for audit"""
    frappe.get_doc({
        "doctype": "Assignment Log",  # Custom DocType
        "todo": todo.name,
        "reference_type": todo.reference_type,
        "reference_name": todo.reference_name,
        "allocated_to": todo.allocated_to,
        "action": action,
        "user": frappe.session.user,
        "timestamp": frappe.utils.now()
    }).insert(ignore_permissions=True)
```
