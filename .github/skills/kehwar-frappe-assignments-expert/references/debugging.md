# Debugging Assignments

Comprehensive guide to troubleshooting assignment issues.

## Table of Contents

1. [Common Issues](#common-issues)
2. [Debugging Tools](#debugging-tools)
3. [Troubleshooting Workflows](#troubleshooting-workflows)
4. [Logging and Monitoring](#logging-and-monitoring)
5. [Database Queries](#database-queries)

## Common Issues

### Issue 1: Assignment Not Created

**Symptoms:**
- Document created but no ToDo generated
- Assignment Rule exists but doesn't trigger

**Causes & Solutions:**

**1. Assignment Rule is Disabled**
```python
# Check rule status
rule = frappe.get_doc("Assignment Rule", "My Rule")
print(f"Disabled: {rule.disabled}")

# Enable rule
rule.disabled = 0
rule.save()
```

**2. Assign Condition Doesn't Match**
```python
# Test condition
doc = frappe.get_doc("Issue", "ISS-001")
rule = frappe.get_doc("Assignment Rule", "My Rule")

result = frappe.safe_eval(rule.assign_condition, None, doc.as_dict())
print(f"Condition result: {result}")

# If False, check field values
print(f"Document fields: {doc.as_dict()}")
```

**3. Assignment Days Mismatch**
```python
# Check if rule is active today
from frappe.utils import get_weekday

rule = frappe.get_doc("Assignment Rule", "My Rule")
today = get_weekday()
assignment_days = [d.day for d in rule.assignment_days]

print(f"Today: {today}")
print(f"Allowed days: {assignment_days}")
print(f"Active today: {today in assignment_days if assignment_days else True}")
```

**4. No Users in Rule**
```python
# Check user pool
rule = frappe.get_doc("Assignment Rule", "My Rule")
users = [u.user for u in rule.users]
print(f"Users: {users}")

# Verify users are enabled
for user in users:
    enabled = frappe.db.get_value("User", user, "enabled")
    print(f"{user}: enabled={enabled}")
```

**5. Document Type Mismatch**
```python
# Verify rule applies to correct DocType
rule = frappe.get_doc("Assignment Rule", "My Rule")
print(f"Rule DocType: {rule.document_type}")
print(f"Document DocType: {doc.doctype}")
```

**6. Rule Execution Skipped**
```python
# Check flags that skip assignment
print(f"in_patch: {frappe.flags.in_patch}")
print(f"in_install: {frappe.flags.in_install}")
print(f"in_setup_wizard: {frappe.flags.in_setup_wizard}")
```

### Issue 2: Assignment to Wrong User

**Symptoms:**
- Assignment created but to unexpected user
- Round Robin not following sequence

**Causes & Solutions:**

**1. Check Last User for Round Robin**
```python
rule = frappe.get_doc("Assignment Rule", "My Rule")
print(f"Last user: {rule.last_user}")

# Verify last_user is in user list
users = [u.user for u in rule.users]
print(f"Users: {users}")
print(f"Last user in list: {rule.last_user in users}")

# Reset last_user if needed
rule.last_user = None
rule.save()
```

**2. Check Workload for Load Balancing**
```python
rule = frappe.get_doc("Assignment Rule", "My Rule")

for user_row in rule.users:
    count = frappe.db.count("ToDo", {
        "allocated_to": user_row.user,
        "reference_type": rule.document_type,
        "status": "Open"
    })
    print(f"{user_row.user}: {count} open assignments")
```

**3. Verify Field Value for Field-Based**
```python
rule = frappe.get_doc("Assignment Rule", "My Rule")
doc = frappe.get_doc(rule.document_type, "DOC-001")

field_value = doc.get(rule.field)
print(f"Field '{rule.field}': {field_value}")

# Check if it's a valid user
if field_value:
    exists = frappe.db.exists("User", field_value)
    enabled = frappe.db.get_value("User", field_value, "enabled")
    print(f"User exists: {exists}, enabled: {enabled}")
```

### Issue 3: Duplicate Assignments

**Symptoms:**
- Multiple ToDo for same user and document
- Assignment created despite existing one

**Causes & Solutions:**

**1. Check for Existing Assignments**
```python
from frappe.desk.form import assign_to

# Get current assignments
assignments = assign_to.get({
    "doctype": "Issue",
    "name": "ISS-001"
})
print(f"Existing assignments: {assignments}")
```

**2. Multiple Rules Matching**
```python
# Check all active rules for DocType
rules = frappe.get_all("Assignment Rule",
    filters={
        "document_type": "Issue",
        "disabled": 0
    },
    fields=["name", "priority", "assign_condition"],
    order_by="priority desc"
)

for rule in rules:
    print(f"{rule.name} (priority {rule.priority}): {rule.assign_condition}")
```

**3. Check Rule Priorities**
```python
# Higher priority should run first
doc = frappe.get_doc("Issue", "ISS-001")

for rule_name in ["Rule A", "Rule B"]:
    rule = frappe.get_doc("Assignment Rule", rule_name)
    matches = frappe.safe_eval(rule.assign_condition, None, doc.as_dict())
    print(f"{rule_name} (priority {rule.priority}): matches={matches}")
```

### Issue 4: Notifications Not Sent

**Symptoms:**
- Assignment created but user didn't receive email
- Notification Log missing

**Causes & Solutions:**

**1. Check Email Queue**
```python
# Check for pending emails
emails = frappe.get_all("Email Queue",
    filters={
        "recipient": "user@example.com",
        "status": ["in", ["Not Sent", "Sending"]]
    },
    fields=["*"],
    order_by="creation desc",
    limit=10
)

for email in emails:
    print(f"{email.subject}: {email.status} - {email.error}")
```

**2. Check Notification Log**
```python
# Check notification was created
notifications = frappe.get_all("Notification Log",
    filters={
        "document_type": "Issue",
        "document_name": "ISS-001",
        "type": "Assignment"
    },
    fields=["*"]
)

for notif in notifications:
    print(f"To: {notif.for_user}, Email sent: {notif.email_sent}")
```

**3. Verify User Email Settings**
```python
user = frappe.get_doc("User", "user@example.com")
print(f"Email: {user.email}")
print(f"Enabled: {user.enabled}")
print(f"Send email: {user.send_me_a_copy}")  # Notification preference
```

**4. Check Muted Flags**
```python
print(f"mute_emails: {frappe.flags.mute_emails}")
print(f"in_test: {frappe.flags.in_test}")
```

**5. Self-Assignment**
```python
# Notifications not sent for self-assignment
todo = frappe.get_doc("ToDo", "TODO-0001")
print(f"Assigned by: {todo.assigned_by}")
print(f"Allocated to: {todo.allocated_to}")
print(f"Self-assigned: {todo.assigned_by == todo.allocated_to}")
```

### Issue 5: Unassign Not Working

**Symptoms:**
- Assignment remains even when unassign_condition is True
- ToDo status not changing to Cancelled

**Causes & Solutions:**

**1. Test Unassign Condition**
```python
doc = frappe.get_doc("Issue", "ISS-001")
rule = frappe.get_doc("Assignment Rule", "My Rule")

if rule.unassign_condition:
    result = frappe.safe_eval(rule.unassign_condition, None, doc.as_dict())
    print(f"Unassign condition result: {result}")
else:
    print("No unassign condition defined")
```

**2. Check Assignment Rule Link**
```python
# Verify ToDo was created by this rule
todos = frappe.get_all("ToDo",
    filters={
        "reference_type": "Issue",
        "reference_name": "ISS-001",
        "status": "Open"
    },
    fields=["name", "assignment_rule"]
)

for todo in todos:
    print(f"ToDo: {todo.name}, Rule: {todo.assignment_rule}")
```

**3. Manual Unassign**
```python
from frappe.desk.form import assign_to

# Force remove assignment
assign_to.remove("Issue", "ISS-001", "user@example.com", ignore_permissions=True)

# Or clear all
assign_to.clear("Issue", "ISS-001", ignore_permissions=True)
```

## Debugging Tools

### Tool 1: Assignment Inspector

```python
def inspect_assignment(doctype, name):
    """Comprehensive assignment inspection"""
    print(f"\n=== Assignment Inspector: {doctype} {name} ===\n")
    
    # 1. Document state
    doc = frappe.get_doc(doctype, name)
    print("Document Fields:")
    print(f"  status: {doc.get('status')}")
    print(f"  priority: {doc.get('priority')}")
    print(f"  _assign: {doc.get('_assign')}")
    
    # 2. Current assignments
    print("\nCurrent Assignments:")
    todos = frappe.get_all("ToDo",
        filters={"reference_type": doctype, "reference_name": name},
        fields=["name", "allocated_to", "status", "assignment_rule", "creation"]
    )
    for todo in todos:
        print(f"  {todo.name}: {todo.allocated_to} ({todo.status}) - {todo.assignment_rule or 'Manual'}")
    
    # 3. Applicable rules
    print("\nApplicable Rules:")
    rules = frappe.get_all("Assignment Rule",
        filters={"document_type": doctype, "disabled": 0},
        fields=["name", "priority", "assign_condition", "unassign_condition"],
        order_by="priority desc"
    )
    
    for rule_data in rules:
        rule = frappe.get_doc("Assignment Rule", rule_data.name)
        
        # Test conditions
        assign_match = frappe.safe_eval(rule.assign_condition, None, doc.as_dict()) if rule.assign_condition else False
        unassign_match = frappe.safe_eval(rule.unassign_condition, None, doc.as_dict()) if rule.unassign_condition else False
        
        print(f"  {rule.name} (priority {rule.priority}):")
        print(f"    Assign: {assign_match}")
        print(f"    Unassign: {unassign_match}")
        print(f"    Users: {[u.user for u in rule.users]}")
        
        # Check assignment days
        if rule.assignment_days:
            from frappe.utils import get_weekday
            today = get_weekday()
            days = [d.day for d in rule.assignment_days]
            print(f"    Days: {days} (active today: {today in days})")
    
    # 4. Share status
    print("\nDocument Shares:")
    shares = frappe.get_all("DocShare",
        filters={"share_doctype": doctype, "share_name": name},
        fields=["user", "read", "write", "submit"]
    )
    for share in shares:
        print(f"  {share.user}: read={share.read}, write={share.write}")
    
    # 5. Recent comments
    print("\nRecent Assignment Comments:")
    comments = frappe.get_all("Comment",
        filters={
            "reference_doctype": doctype,
            "reference_name": name,
            "comment_type": ["in", ["Assigned", "Assignment Completed"]]
        },
        fields=["content", "owner", "creation"],
        order_by="creation desc",
        limit=5
    )
    for comment in comments:
        print(f"  {comment.creation}: {comment.content[:50]}...")
```

### Tool 2: Rule Simulator

```python
def simulate_assignment_rule(rule_name, doc_dict):
    """Simulate assignment rule execution"""
    rule = frappe.get_doc("Assignment Rule", rule_name)
    
    print(f"\n=== Simulating Rule: {rule_name} ===\n")
    
    # Test assign condition
    print("1. Assign Condition:")
    print(f"   Expression: {rule.assign_condition}")
    try:
        assign_result = frappe.safe_eval(rule.assign_condition, None, doc_dict)
        print(f"   Result: {assign_result}")
    except Exception as e:
        print(f"   Error: {str(e)}")
        assign_result = False
    
    # Test unassign condition
    if rule.unassign_condition:
        print("\n2. Unassign Condition:")
        print(f"   Expression: {rule.unassign_condition}")
        try:
            unassign_result = frappe.safe_eval(rule.unassign_condition, None, doc_dict)
            print(f"   Result: {unassign_result}")
        except Exception as e:
            print(f"   Error: {str(e)}")
    
    # Check assignment days
    print("\n3. Assignment Days:")
    if rule.assignment_days:
        from frappe.utils import get_weekday
        today = get_weekday()
        days = [d.day for d in rule.assignment_days]
        print(f"   Configured: {days}")
        print(f"   Today: {today}")
        print(f"   Active: {today in days}")
    else:
        print("   No restriction (all days)")
    
    # Show user selection
    print("\n4. User Selection:")
    print(f"   Strategy: {rule.rule}")
    
    if rule.rule == "Round Robin":
        print(f"   Last user: {rule.last_user}")
        users = [u.user for u in rule.users]
        print(f"   Users: {users}")
        if rule.last_user:
            idx = users.index(rule.last_user) if rule.last_user in users else -1
            next_idx = (idx + 1) % len(users)
            print(f"   Next user: {users[next_idx]}")
    
    elif rule.rule == "Load Balancing":
        print("   Current workload:")
        for user in rule.users:
            count = frappe.db.count("ToDo", {
                "allocated_to": user.user,
                "reference_type": rule.document_type,
                "status": "Open"
            })
            print(f"     {user.user}: {count}")
    
    elif rule.rule == "Based on Field":
        field_value = doc_dict.get(rule.field)
        print(f"   Field: {rule.field}")
        print(f"   Value: {field_value}")
        if field_value:
            exists = frappe.db.exists("User", field_value)
            print(f"   Valid user: {exists}")
    
    # Final verdict
    print("\n5. Execution Result:")
    if assign_result:
        print("   ✓ Assignment would be created")
    else:
        print("   ✗ Assignment would NOT be created")

# Usage
doc = frappe.get_doc("Issue", "ISS-001")
simulate_assignment_rule("My Rule", doc.as_dict())
```

### Tool 3: Assignment History Tracker

```python
def get_assignment_history(doctype, name):
    """Get complete assignment history"""
    print(f"\n=== Assignment History: {doctype} {name} ===\n")
    
    # All todos (including cancelled/closed)
    todos = frappe.get_all("ToDo",
        filters={"reference_type": doctype, "reference_name": name},
        fields=["name", "allocated_to", "assigned_by", "status", "creation", "modified"],
        order_by="creation asc"
    )
    
    print(f"Total assignments: {len(todos)}\n")
    
    for todo in todos:
        print(f"{todo.creation}: {todo.assigned_by} → {todo.allocated_to}")
        print(f"  Status: {todo.status}")
        if todo.modified != todo.creation:
            print(f"  Modified: {todo.modified}")
        print()
```

### Tool 4: Email Debug Helper

```python
def debug_assignment_emails(user_email):
    """Debug email notifications for user"""
    print(f"\n=== Email Debug for {user_email} ===\n")
    
    # User settings
    user = frappe.get_doc("User", user_email)
    print("User Settings:")
    print(f"  Email: {user.email}")
    print(f"  Enabled: {user.enabled}")
    print(f"  Email signature: {bool(user.email_signature)}")
    
    # Recent email queue
    print("\nRecent Emails:")
    emails = frappe.get_all("Email Queue",
        filters={"recipient": user_email},
        fields=["subject", "status", "modified", "error"],
        order_by="modified desc",
        limit=10
    )
    for email in emails:
        print(f"  {email.modified}: {email.subject}")
        print(f"    Status: {email.status}")
        if email.error:
            print(f"    Error: {email.error}")
    
    # Recent notifications
    print("\nRecent Notifications:")
    notifications = frappe.get_all("Notification Log",
        filters={"for_user": user_email, "type": "Assignment"},
        fields=["subject", "email_sent", "creation"],
        order_by="creation desc",
        limit=10
    )
    for notif in notifications:
        print(f"  {notif.creation}: {notif.subject}")
        print(f"    Email sent: {notif.email_sent}")
```

## Troubleshooting Workflows

### Workflow 1: Assignment Not Created

```
1. Verify rule exists and is enabled
   → Check Assignment Rule list
   → Verify disabled = 0

2. Check document matches assign_condition
   → Get document: frappe.get_doc(doctype, name)
   → Test condition with doc.as_dict()
   → Verify all field values

3. Check assignment days
   → Get current weekday
   → Compare with rule.assignment_days
   → Verify rule is active today

4. Check user pool
   → Verify users exist
   → Check users are enabled
   → Ensure at least one user available

5. Check for execution flags
   → frappe.flags.in_patch
   → frappe.flags.in_install
   → Any custom flags that skip assignment

6. Test manually
   → from frappe.automation.doctype.assignment_rule.assignment_rule import apply
   → apply(doc)
   → Check for errors in console
```

### Workflow 2: Wrong User Assigned

```
1. Identify rule type
   → Round Robin: Check last_user
   → Load Balancing: Check workload counts
   → Field-Based: Check field value

2. Verify user pool
   → Get all users from rule
   → Check each is valid and enabled

3. Test rule logic
   → For Round Robin: Verify user sequence
   → For Load Balancing: Query current assignments
   → For Field-Based: Check field contains valid user

4. Check priority conflicts
   → List all rules for DocType
   → Sort by priority
   → Identify which rule runs first

5. Reset if needed
   → Clear last_user for Round Robin
   → Redistribute for Load Balancing
   → Fix field value for Field-Based
```

### Workflow 3: Notification Not Received

```
1. Check ToDo was created
   → Query ToDo table
   → Verify allocated_to is correct

2. Check Notification Log
   → Search for Assignment type
   → Verify for_user matches

3. Check Email Queue
   → Find email by recipient
   → Check status and error fields

4. Verify user email settings
   → User.email is set
   → User is enabled
   → No email blocks

5. Check system email settings
   → SMTP configured
   → Email account active
   → Test email sending

6. Check for mute flags
   → frappe.flags.mute_emails
   → frappe.flags.in_test
   → Custom suppression logic
```

## Logging and Monitoring

### Enable Debug Logging

```python
# In site_config.json
{
    "developer_mode": 1,
    "logging": 2
}

# In code
import logging
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger("frappe.automation")
logger.setLevel(logging.DEBUG)
```

### Log Assignment Events

```python
# Add to assignment_rule.py
def apply(doc, method=None):
    frappe.logger().debug(f"Applying assignment rules to {doc.doctype} {doc.name}")
    
    # ... existing logic ...
    
    if new_assignment:
        frappe.logger().info(f"Created assignment for {doc.name} to {user}")
    else:
        frappe.logger().debug(f"No assignment created for {doc.name}")
```

### Custom Logging

```python
class AssignmentLogger:
    @staticmethod
    def log_rule_execution(rule_name, doc, result):
        log_entry = frappe.get_doc({
            "doctype": "Assignment Debug Log",  # Custom DocType
            "rule": rule_name,
            "document_type": doc.doctype,
            "document_name": doc.name,
            "result": result,
            "timestamp": frappe.utils.now()
        })
        log_entry.insert(ignore_permissions=True)
```

## Database Queries

### Query 1: Find Unassigned Documents

```sql
SELECT t.name, t.status, t.priority
FROM `tabIssue` t
LEFT JOIN `tabToDo` todo ON todo.reference_name = t.name
    AND todo.reference_type = 'Issue'
    AND todo.status = 'Open'
WHERE t.status = 'Open'
    AND todo.name IS NULL
ORDER BY t.priority DESC, t.creation ASC
```

### Query 2: Assignment Workload Distribution

```sql
SELECT allocated_to,
       COUNT(*) as total,
       SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as open,
       SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed
FROM `tabToDo`
WHERE reference_type = 'Issue'
GROUP BY allocated_to
ORDER BY open DESC
```

### Query 3: Overdue Assignments

```sql
SELECT t.name, t.allocated_to, t.reference_type, t.reference_name,
       t.date as due_date, DATEDIFF(CURDATE(), t.date) as days_overdue
FROM `tabToDo` t
WHERE t.status = 'Open'
    AND t.date < CURDATE()
ORDER BY days_overdue DESC
```

### Query 4: Assignment Rule Effectiveness

```sql
SELECT ar.name as rule_name,
       COUNT(DISTINCT t.name) as assignments_created,
       AVG(TIMESTAMPDIFF(HOUR, t.creation, t.modified)) as avg_completion_hours
FROM `tabAssignment Rule` ar
LEFT JOIN `tabToDo` t ON t.assignment_rule = ar.name
WHERE ar.disabled = 0
GROUP BY ar.name
ORDER BY assignments_created DESC
```

### Query 5: Stuck Assignments

```sql
SELECT t.name, t.allocated_to, t.reference_type, t.reference_name,
       t.creation, DATEDIFF(NOW(), t.modified) as days_stale
FROM `tabToDo` t
WHERE t.status = 'Open'
    AND t.modified < DATE_SUB(NOW(), INTERVAL 30 DAY)
ORDER BY days_stale DESC
```
