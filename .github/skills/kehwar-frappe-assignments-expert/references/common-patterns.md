# Common Assignment Patterns

Collection of proven assignment patterns for various use cases.

## Table of Contents

1. [Support and Issue Tracking](#support-and-issue-tracking)
2. [Sales and Leads](#sales-and-leads)
3. [Approval Workflows](#approval-workflows)
4. [Project Management](#project-management)
5. [Service Level Agreements (SLA)](#service-level-agreements-sla)
6. [Escalation Patterns](#escalation-patterns)
7. [Team-Based Assignment](#team-based-assignment)
8. [Conditional Assignment](#conditional-assignment)

## Support and Issue Tracking

### Pattern 1: Round Robin Support Queue

Distribute support tickets evenly across team.

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Support Ticket Distribution",
    "document_type": "Issue",
    "assign_condition": "status == 'Open' and issue_type == 'Support'",
    "unassign_condition": "status in ('Closed', 'Resolved')",
    "rule": "Round Robin",
    "users": [
        {"user": "support1@example.com"},
        {"user": "support2@example.com"},
        {"user": "support3@example.com"}
    ]
}).insert()
```

### Pattern 2: Priority-Based Assignment

Assign based on ticket priority with different teams.

```python
# Critical - Senior team
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Critical Issues",
    "document_type": "Issue",
    "priority": 10,
    "assign_condition": "priority == 'Critical' and status == 'Open'",
    "rule": "Load Balancing",
    "users": [
        {"user": "senior1@example.com"},
        {"user": "senior2@example.com"}
    ]
}).insert()

# High - Regular team
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "High Priority Issues",
    "document_type": "Issue",
    "priority": 5,
    "assign_condition": "priority == 'High' and status == 'Open'",
    "rule": "Load Balancing",
    "users": [
        {"user": "support1@example.com"},
        {"user": "support2@example.com"}
    ]
}).insert()

# Medium/Low - Junior team
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Standard Issues",
    "document_type": "Issue",
    "priority": 0,
    "assign_condition": "priority in ('Medium', 'Low') and status == 'Open'",
    "rule": "Round Robin",
    "users": [
        {"user": "junior1@example.com"},
        {"user": "junior2@example.com"}
    ]
}).insert()
```

### Pattern 3: Category-Based Routing

Route to specialized teams based on issue category.

```python
# Technical issues
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Technical Support",
    "document_type": "Issue",
    "assign_condition": "category == 'Technical' and status == 'Open'",
    "rule": "Load Balancing",
    "users": [
        {"user": "tech.support1@example.com"},
        {"user": "tech.support2@example.com"}
    ]
}).insert()

# Billing issues
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Billing Support",
    "document_type": "Issue",
    "assign_condition": "category == 'Billing' and status == 'Open'",
    "rule": "Round Robin",
    "users": [
        {"user": "billing1@example.com"},
        {"user": "billing2@example.com"}
    ]
}).insert()
```

## Sales and Leads

### Pattern 4: Territory-Based Lead Assignment

Assign leads to territory managers.

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Territory-Based Leads",
    "document_type": "Lead",
    "assign_condition": "status == 'Open' and territory_manager",
    "rule": "Based on Field",
    "field": "territory_manager"
}).insert()
```

### Pattern 5: Lead Score Based Assignment

Route high-value leads to senior sales team.

```python
# High score - Senior sales
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "High Value Leads",
    "document_type": "Lead",
    "priority": 10,
    "assign_condition": "status == 'Open' and lead_score >= 80",
    "rule": "Round Robin",
    "users": [
        {"user": "senior.sales1@example.com"},
        {"user": "senior.sales2@example.com"}
    ]
}).insert()

# Standard leads
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Standard Leads",
    "document_type": "Lead",
    "priority": 0,
    "assign_condition": "status == 'Open' and lead_score < 80",
    "rule": "Load Balancing",
    "users": [
        {"user": "sales1@example.com"},
        {"user": "sales2@example.com"},
        {"user": "sales3@example.com"}
    ]
}).insert()
```

### Pattern 6: Account Manager Assignment

Assign opportunities to account managers of existing customers.

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Account Manager Opportunities",
    "document_type": "Opportunity",
    "assign_condition": "status == 'Open' and account_manager",
    "rule": "Based on Field",
    "field": "account_manager"
}).insert()
```

## Approval Workflows

### Pattern 7: Amount-Based Approvals

Multi-tier approval based on transaction value.

```python
# > $100K - CFO
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "CFO Approval",
    "document_type": "Purchase Order",
    "priority": 30,
    "assign_condition": "docstatus == 0 and grand_total > 100000",
    "close_condition": "docstatus in (1, 2)",
    "rule": "Based on Field",
    "field": "cfo_approver"
}).insert()

# $50K-$100K - Finance Manager
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Finance Manager Approval",
    "document_type": "Purchase Order",
    "priority": 20,
    "assign_condition": "docstatus == 0 and grand_total > 50000 and grand_total <= 100000",
    "close_condition": "docstatus in (1, 2)",
    "rule": "Round Robin",
    "users": [
        {"user": "finance.manager1@example.com"},
        {"user": "finance.manager2@example.com"}
    ]
}).insert()

# < $50K - Department Manager
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Department Manager Approval",
    "document_type": "Purchase Order",
    "priority": 10,
    "assign_condition": "docstatus == 0 and grand_total <= 50000",
    "close_condition": "docstatus in (1, 2)",
    "rule": "Based on Field",
    "field": "department_approver"
}).insert()
```

### Pattern 8: Leave Approval Hierarchy

Multi-stage leave approvals.

```python
# Stage 1: Manager approval
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Manager Leave Approval",
    "document_type": "Leave Application",
    "priority": 10,
    "assign_condition": "workflow_state == 'Pending Manager Approval'",
    "close_condition": "workflow_state != 'Pending Manager Approval'",
    "rule": "Based on Field",
    "field": "leave_approver"
}).insert()

# Stage 2: HR approval for long leaves
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "HR Leave Approval",
    "document_type": "Leave Application",
    "priority": 20,
    "assign_condition": "workflow_state == 'Pending HR Approval' and total_leave_days > 5",
    "close_condition": "workflow_state in ('Approved', 'Rejected')",
    "rule": "Round Robin",
    "users": [
        {"user": "hr1@example.com"},
        {"user": "hr2@example.com"}
    ]
}).insert()
```

### Pattern 9: Document Review Workflow

Sequential review and approval.

```python
class Contract(Document):
    def on_update(self):
        from frappe.desk.form import assign_to
        
        # Legal review
        if self.workflow_state == "Pending Legal Review":
            assign_to.clear(self.doctype, self.name, ignore_permissions=True)
            assign_to.add({
                "assign_to": ["legal@example.com"],
                "doctype": self.doctype,
                "name": self.name,
                "description": f"Legal review required for {self.name}",
                "priority": "High"
            }, ignore_permissions=True)
        
        # Finance review
        elif self.workflow_state == "Pending Finance Review":
            assign_to.clear(self.doctype, self.name, ignore_permissions=True)
            assign_to.add({
                "assign_to": ["finance@example.com"],
                "doctype": self.doctype,
                "name": self.name,
                "description": f"Finance review required for {self.name}",
                "priority": "High"
            }, ignore_permissions=True)
        
        # Final approval
        elif self.workflow_state == "Pending Final Approval":
            assign_to.clear(self.doctype, self.name, ignore_permissions=True)
            assign_to.add({
                "assign_to": [self.approver],
                "doctype": self.doctype,
                "name": self.name,
                "description": f"Final approval for {self.name}",
                "priority": "High"
            }, ignore_permissions=True)
```

## Project Management

### Pattern 10: Task Assignment by Project Manager

Auto-assign tasks to team members.

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Project Task Assignment",
    "document_type": "Task",
    "assign_condition": "status == 'Open' and assigned_to",
    "close_condition": "status in ('Completed', 'Cancelled')",
    "rule": "Based on Field",
    "field": "assigned_to",
    "due_date_based_on": "exp_end_date"
}).insert()
```

### Pattern 11: Milestone Review Assignment

Assign milestone reviews to stakeholders.

```python
class ProjectMilestone(Document):
    def on_update(self):
        from frappe.desk.form import assign_to
        
        if self.status == "Completed" and not self.reviewed:
            # Get project stakeholders
            stakeholders = frappe.get_all("Project User",
                filters={"parent": self.project, "role": "Stakeholder"},
                pluck="user"
            )
            
            if stakeholders:
                assign_to.add({
                    "assign_to": stakeholders,
                    "doctype": self.doctype,
                    "name": self.name,
                    "description": f"Review milestone: {self.milestone_name}",
                    "priority": "Medium",
                    "date": frappe.utils.add_days(frappe.utils.today(), 3)
                }, ignore_permissions=True)
```

### Pattern 12: Sprint Task Distribution

Distribute sprint tasks using load balancing.

```python
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Sprint Task Distribution",
    "document_type": "Task",
    "assign_condition": "status == 'Open' and sprint and not assigned_to",
    "rule": "Load Balancing",
    "users": [
        {"user": "dev1@example.com"},
        {"user": "dev2@example.com"},
        {"user": "dev3@example.com"}
    ],
    "due_date_based_on": "exp_end_date"
}).insert()
```

## Service Level Agreements (SLA)

### Pattern 13: SLA-Based Priority Assignment

Assign based on SLA requirements.

```python
class SupportTicket(Document):
    def on_update(self):
        from frappe.desk.form import assign_to
        from frappe.utils import add_to_date, now_datetime
        
        if self.has_value_changed("sla_priority"):
            # Clear existing
            assign_to.clear(self.doctype, self.name, ignore_permissions=True)
            
            # SLA response times
            sla_config = {
                "Critical": {"hours": 1, "team": ["oncall@example.com"]},
                "High": {"hours": 4, "team": ["senior1@example.com", "senior2@example.com"]},
                "Medium": {"hours": 24, "team": ["support@example.com"]},
                "Low": {"hours": 48, "team": ["support@example.com"]}
            }
            
            config = sla_config.get(self.sla_priority)
            if config:
                due = add_to_date(now_datetime(), hours=config["hours"])
                
                assign_to.add({
                    "assign_to": config["team"],
                    "doctype": self.doctype,
                    "name": self.name,
                    "description": f"SLA: Respond within {config['hours']}h",
                    "priority": "High" if config["hours"] <= 4 else "Medium",
                    "date": due.strftime("%Y-%m-%d")
                }, ignore_permissions=True)
```

### Pattern 14: SLA Breach Prevention

Auto-escalate before SLA breach.

```python
def check_sla_breach():
    """Scheduled job to prevent SLA breaches"""
    from frappe.utils import now_datetime, get_datetime
    from frappe.desk.form import assign_to
    
    # Find tickets nearing SLA breach (within 1 hour)
    at_risk = frappe.get_all("ToDo",
        filters={
            "status": "Open",
            "reference_type": "Support Ticket",
            "date": ["<=", frappe.utils.add_to_date(now_datetime(), hours=1)]
        },
        fields=["reference_name", "allocated_to", "date"]
    )
    
    for todo in at_risk:
        ticket = frappe.get_doc("Support Ticket", todo.reference_name)
        
        # Assign to supervisor
        supervisor = frappe.db.get_value("User", todo.allocated_to, "supervisor")
        if supervisor:
            assign_to.add({
                "assign_to": [supervisor],
                "doctype": "Support Ticket",
                "name": todo.reference_name,
                "description": f"SLA ALERT: Ticket due in <1 hour, assigned to {todo.allocated_to}",
                "priority": "High"
            }, ignore_permissions=True)
```

## Escalation Patterns

### Pattern 15: Time-Based Escalation

Escalate overdue assignments to managers.

```python
def escalate_overdue():
    """Scheduled hourly to check for overdue assignments"""
    from frappe.utils import today, add_days
    from frappe.desk.form import assign_to
    
    overdue_date = add_days(today(), -2)
    
    overdue = frappe.get_all("ToDo",
        filters={
            "status": "Open",
            "date": ["<", overdue_date]
        },
        fields=["name", "allocated_to", "reference_type", "reference_name", "description"]
    )
    
    for todo in overdue:
        manager = frappe.db.get_value("User", todo.allocated_to, "manager")
        
        if manager:
            assign_to.add({
                "assign_to": [manager],
                "doctype": todo.reference_type,
                "name": todo.reference_name,
                "description": f"ESCALATED: {todo.description}<br><br>Original: {todo.allocated_to}<br>Overdue since: {todo.date}",
                "priority": "High"
            }, ignore_permissions=True)
            
            # Add escalation comment
            doc = frappe.get_doc(todo.reference_type, todo.reference_name)
            doc.add_comment("Info", f"Escalated to {manager} - overdue assignment")
```

### Pattern 16: Hierarchical Escalation

Multi-level escalation based on time elapsed.

```python
def hierarchical_escalation():
    from frappe.utils import get_datetime, date_diff, now
    from frappe.desk.form import assign_to
    
    open_todos = frappe.get_all("ToDo",
        filters={"status": "Open"},
        fields=["name", "creation", "allocated_to", "reference_type", "reference_name"]
    )
    
    for todo in open_todos:
        age_days = date_diff(now(), todo.creation)
        user = todo.allocated_to
        
        # Level 1: 3 days - notify team lead
        if age_days >= 3:
            team_lead = frappe.db.get_value("User", user, "team_lead")
            if team_lead:
                notify_escalation(todo, team_lead, "Team Lead", age_days)
        
        # Level 2: 5 days - notify manager
        if age_days >= 5:
            manager = frappe.db.get_value("User", user, "manager")
            if manager:
                notify_escalation(todo, manager, "Manager", age_days)
        
        # Level 3: 7 days - notify department head
        if age_days >= 7:
            dept_head = frappe.db.get_value("User", user, "department_head")
            if dept_head:
                notify_escalation(todo, dept_head, "Department Head", age_days)

def notify_escalation(todo, escalation_user, level, age_days):
    from frappe.desk.form import assign_to
    
    # Check if already escalated to this level
    existing = frappe.db.exists("ToDo", {
        "reference_type": todo.reference_type,
        "reference_name": todo.reference_name,
        "allocated_to": escalation_user,
        "status": "Open"
    })
    
    if not existing:
        assign_to.add({
            "assign_to": [escalation_user],
            "doctype": todo.reference_type,
            "name": todo.reference_name,
            "description": f"ESCALATION ({level}): Assignment pending for {age_days} days<br>Original assignee: {todo.allocated_to}",
            "priority": "High"
        }, ignore_permissions=True)
```

## Team-Based Assignment

### Pattern 17: Department-Based Routing

Route to department teams.

```python
# Engineering department
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Engineering Issues",
    "document_type": "Issue",
    "assign_condition": "department == 'Engineering' and status == 'Open'",
    "rule": "Load Balancing",
    "users": [
        {"user": "eng1@example.com"},
        {"user": "eng2@example.com"},
        {"user": "eng3@example.com"}
    ]
}).insert()

# Sales department
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Sales Issues",
    "document_type": "Issue",
    "assign_condition": "department == 'Sales' and status == 'Open'",
    "rule": "Round Robin",
    "users": [
        {"user": "sales1@example.com"},
        {"user": "sales2@example.com"}
    ]
}).insert()
```

### Pattern 18: Skill-Based Routing

Assign based on required skills.

```python
class Task(Document):
    def on_update(self):
        from frappe.desk.form import assign_to
        
        if self.status == "Open" and self.required_skill and not self.assigned_to:
            # Get users with required skill
            skilled_users = frappe.get_all("User Skill",
                filters={"skill": self.required_skill, "proficiency_level": [">=", 3]},
                fields=["parent as user"]
            )
            
            if skilled_users:
                # Find user with least workload
                workload = []
                for user in skilled_users:
                    count = frappe.db.count("ToDo",
                        filters={"allocated_to": user.user, "status": "Open"}
                    )
                    workload.append({"user": user.user, "count": count})
                
                workload.sort(key=lambda x: x["count"])
                
                assign_to.add({
                    "assign_to": [workload[0]["user"]],
                    "doctype": self.doctype,
                    "name": self.name,
                    "description": f"Task requires {self.required_skill}",
                    "priority": self.priority
                }, ignore_permissions=True)
```

### Pattern 19: On-Call Rotation

Assign to on-call team member.

```python
def get_oncall_user():
    """Get current on-call user based on schedule"""
    from frappe.utils import now_datetime, get_weekday
    
    today = get_weekday()
    current_hour = now_datetime().hour
    
    # Define on-call schedule
    schedule = {
        "Monday": {"day": "oncall1@example.com", "night": "oncall2@example.com"},
        "Tuesday": {"day": "oncall1@example.com", "night": "oncall2@example.com"},
        # ... more days
    }
    
    shift = "day" if 8 <= current_hour < 20 else "night"
    return schedule.get(today, {}).get(shift)

# Use in assignment
frappe.get_doc({
    "doctype": "Assignment Rule",
    "name": "Critical Incidents",
    "document_type": "Incident",
    "assign_condition": "severity == 'Critical'",
    "rule": "Based on Field",
    "field": "oncall_user"  # Set this field via custom logic
}).insert()
```

## Conditional Assignment

### Pattern 20: Customer-Specific Assignment

Assign based on customer relationships.

```python
class SalesOrder(Document):
    def on_submit(self):
        from frappe.desk.form import assign_to
        
        # Get account manager for customer
        account_manager = frappe.db.get_value("Customer", self.customer, "account_manager")
        
        if account_manager:
            assign_to.add({
                "assign_to": [account_manager],
                "doctype": self.doctype,
                "name": self.name,
                "description": f"Process order for {self.customer}",
                "priority": "High" if self.grand_total > 50000 else "Medium"
            }, ignore_permissions=True)
```
