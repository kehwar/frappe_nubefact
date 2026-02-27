# Assignment Notifications Reference

Complete guide to notification configuration and customization for assignments.

## Table of Contents

1. [Notification Types](#notification-types)
2. [Notification Flow](#notification-flow)
3. [Configuration](#configuration)
4. [Customization](#customization)
5. [Suppression](#suppression)

## Notification Types

### Assignment Created

Sent when a new assignment is created.

**Recipients:** `allocated_to` (assignee)

**Trigger:** `assign_to.add()` called

**Subject:**
```
{Assigner} assigned a new task {DocType} {Title} to you
```

**Content:**
- Task description (HTML)
- Document link
- Priority indicator
- Due date (if set)

**Example:**
```
Subject: John Doe assigned a new task Issue ISS-001 to you

Body:
Please investigate the customer complaint about billing errors.

Priority: High
Due Date: 2024-02-15

[View Document]
```

### Assignment Removed

Sent when assignment is cancelled/removed.

**Recipients:** `allocated_to` (assignee)

**Trigger:** `assign_to.remove()` or unassign_condition

**Subject:**
```
Your assignment on {DocType} {Title} has been removed by {User}
```

**Example:**
```
Subject: Your assignment on Issue ISS-001 has been removed by Admin

Body:
The assignment has been cancelled.

[View Document]
```

### Assignment Completed

Sent when assignment is closed.

**Recipients:** `assigned_by` (assigner)

**Trigger:** `assign_to.close()`

**Subject:**
```
Assignment completed on {DocType} {Title}
```

**Example:**
```
Subject: Assignment completed on Issue ISS-001

Body:
User@example.com has completed the assigned task.

[View Document]
```

## Notification Flow

### Creation Flow

```
1. assign_to.add() called
   ↓
2. ToDo document created
   ↓
3. notify_assignment() called with action="ASSIGN"
   ↓
4. Check if assigned_by == allocated_to (skip if True)
   ↓
5. Check if user is enabled (skip if False)
   ↓
6. Get user language preference
   ↓
7. Build notification content
   ↓
8. Create Notification Log
   ↓
9. Enqueue email creation
   ↓
10. Email Queue processes
    ↓
11. SMTP sends email
    ↓
12. User receives notification
```

### Email Queue Processing

```python
# Email Queue document structure
{
    "recipient": "user@example.com",
    "subject": "John assigned a task to you",
    "message": "<html>...</html>",
    "status": "Not Sent",  # → "Sent" or "Error"
    "priority": 1,
    "retry": 0,
    "error": None
}
```

## Configuration

### System-Level Settings

```python
# Site configuration (site_config.json)
{
    "mail_server": "smtp.gmail.com",
    "mail_port": 587,
    "use_tls": 1,
    "mail_login": "notifications@example.com",
    "mail_password": "password",
    "auto_email_id": "notifications@example.com"
}
```

### Email Account Setup

```python
# Create Email Account
email_account = frappe.get_doc({
    "doctype": "Email Account",
    "email_id": "notifications@example.com",
    "email_account_name": "Notifications",
    "domain": "smtp.gmail.com",
    "use_imap": 0,
    "use_ssl": 1,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "enable_outgoing": 1,
    "default_outgoing": 1
})
email_account.insert()
```

### User Notification Preferences

```python
# User settings
user = frappe.get_doc("User", "user@example.com")

# Email notifications
user.thread_notify = 1  # Email for document comments/assignments

# Follow assigned documents
user.follow_assigned_documents = 1  # Auto-follow on assignment

# Email digest
user.send_me_a_copy = 1  # Receive email copy

user.save()
```

### Notification Log Settings

```python
# Global notification settings
notification_settings = frappe.get_doc("Notification Settings")

# Enable notifications
notification_settings.enabled = 1

# Batch size for email sending
notification_settings.batch_size = 100

notification_settings.save()
```

## Customization

### Custom Email Template

Create custom email template for assignments:

```python
# Create Email Template
template = frappe.get_doc({
    "doctype": "Email Template",
    "name": "Assignment Notification",
    "subject": "New Task: {{ doc.description }}",
    "response": """
    <div style="padding: 20px; font-family: Arial;">
        <h2>New Assignment</h2>
        
        <p>Hello {{ allocated_to }},</p>
        
        <p>{{ assigned_by }} has assigned you a new task:</p>
        
        <div style="background: #f5f5f5; padding: 15px; margin: 15px 0;">
            <strong>{{ reference_type }} {{ reference_name }}</strong><br>
            {{ description }}
        </div>
        
        <table style="margin: 15px 0;">
            <tr>
                <td><strong>Priority:</strong></td>
                <td>{{ priority }}</td>
            </tr>
            {% if date %}
            <tr>
                <td><strong>Due Date:</strong></td>
                <td>{{ date }}</td>
            </tr>
            {% endif %}
        </table>
        
        <p>
            <a href="{{ frappe.utils.get_url() }}/app/{{ reference_type.lower() }}/{{ reference_name }}" 
               style="background: #0089ff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                View Document
            </a>
        </p>
        
        <p style="color: #666; font-size: 12px; margin-top: 30px;">
            This is an automated notification from {{ frappe.utils.get_url() }}
        </p>
    </div>
    """
})
template.insert()
```

### Use Custom Template

Modify `notify_assignment()` to use custom template:

```python
def custom_notify_assignment(assigned_by, allocated_to, doc_type, doc_name, action="ASSIGN", description=None):
    """Custom notification with template"""
    if not (assigned_by and allocated_to and doc_type and doc_name):
        return
    
    # Skip self-assignment
    if assigned_by == allocated_to:
        return
    
    # Get document
    doc = frappe.get_doc(doc_type, doc_name)
    
    # Get template
    template = frappe.get_doc("Email Template", "Assignment Notification")
    
    # Render template
    context = {
        "doc": doc,
        "assigned_by": assigned_by,
        "allocated_to": allocated_to,
        "reference_type": doc_type,
        "reference_name": doc_name,
        "description": description or doc.get("subject") or doc.name,
        "priority": "High",  # or get from doc
        "date": doc.get("due_date")
    }
    
    subject = frappe.render_template(template.subject, context)
    message = frappe.render_template(template.response, context)
    
    # Send email
    frappe.sendmail(
        recipients=[allocated_to],
        subject=subject,
        message=message,
        reference_doctype=doc_type,
        reference_name=doc_name
    )
```

### Add Custom Fields to Notification

Include additional context in notifications:

```python
def enhanced_notify_assignment(todo):
    """Enhanced notification with additional context"""
    doc = frappe.get_doc(todo.reference_type, todo.reference_name)
    
    # Build context
    context = {
        "assignee": frappe.get_cached_value("User", todo.allocated_to, "full_name"),
        "assigner": frappe.get_cached_value("User", todo.assigned_by, "full_name"),
        "document_title": doc.get("title") or doc.get("subject") or doc.name,
        "priority": todo.priority,
        "due_date": todo.date,
        "description": todo.description,
        "custom_field": doc.get("custom_field")  # Add custom fields
    }
    
    # Custom message
    message = frappe.render_template("""
    <div>
        <p>Hi {{ assignee }},</p>
        
        <p>{{ assigner }} assigned you: {{ document_title }}</p>
        
        <p>{{ description }}</p>
        
        {% if custom_field %}
        <p><strong>Special Note:</strong> {{ custom_field }}</p>
        {% endif %}
        
        <p>Priority: {{ priority }}</p>
        {% if due_date %}
        <p>Due: {{ due_date }}</p>
        {% endif %}
    </div>
    """, context)
    
    frappe.sendmail(
        recipients=[todo.allocated_to],
        subject=f"New Assignment: {context['document_title']}",
        message=message
    )
```

### Notification Hooks

Override default notification behavior:

```python
# In hooks.py
doc_events = {
    "ToDo": {
        "after_insert": "myapp.notifications.custom_todo_notification"
    }
}

# In myapp/notifications.py
def custom_todo_notification(doc, method):
    """Custom notification logic"""
    if doc.reference_type and doc.reference_name:
        # Send custom notification
        send_custom_assignment_email(doc)
        
        # Send Slack notification
        send_slack_notification(doc)
        
        # Log to external system
        log_to_external_system(doc)

def send_slack_notification(todo):
    """Send Slack notification for assignment"""
    import requests
    
    slack_webhook = frappe.conf.get("slack_webhook_url")
    if not slack_webhook:
        return
    
    message = {
        "text": f"New Assignment: {todo.description}",
        "attachments": [{
            "color": "#0089ff",
            "fields": [
                {"title": "Assigned To", "value": todo.allocated_to, "short": True},
                {"title": "Priority", "value": todo.priority, "short": True},
                {"title": "Document", "value": f"{todo.reference_type} {todo.reference_name}"}
            ]
        }]
    }
    
    requests.post(slack_webhook, json=message)
```

### Priority-Based Notification

Send different notifications based on priority:

```python
def priority_based_notification(todo):
    """Send notification based on priority"""
    priority_config = {
        "High": {
            "subject_prefix": "🔴 URGENT",
            "sms": True,
            "push": True
        },
        "Medium": {
            "subject_prefix": "🟡",
            "sms": False,
            "push": True
        },
        "Low": {
            "subject_prefix": "🟢",
            "sms": False,
            "push": False
        }
    }
    
    config = priority_config.get(todo.priority, priority_config["Medium"])
    
    # Email notification
    subject = f"{config['subject_prefix']} New Assignment: {todo.description}"
    frappe.sendmail(
        recipients=[todo.allocated_to],
        subject=subject,
        message=build_email_message(todo)
    )
    
    # SMS if configured
    if config["sms"]:
        send_sms_notification(todo)
    
    # Push notification if configured
    if config["push"]:
        send_push_notification(todo)
```

## Suppression

### Global Suppression

```python
# Suppress all emails temporarily
frappe.flags.mute_emails = True

# Your assignment code
assign_to.add({...})

# Re-enable
frappe.flags.mute_emails = False
```

### Test Mode Suppression

```python
# Automatically suppressed in tests
frappe.flags.in_test = True
assign_to.add({...})
frappe.flags.in_test = False
```

### Conditional Suppression

```python
def assign_with_notification_control(doctype, name, users, send_notification=True):
    """Control notification sending"""
    if not send_notification:
        frappe.flags.mute_emails = True
    
    from frappe.desk.form import assign_to
    assign_to.add({
        "assign_to": users,
        "doctype": doctype,
        "name": name
    })
    
    if not send_notification:
        frappe.flags.mute_emails = False
```

### User-Level Suppression

```python
# Check user preferences
def should_send_notification(user):
    """Check if user wants notifications"""
    user_doc = frappe.get_doc("User", user)
    return user_doc.thread_notify and user_doc.enabled

# Usage
if should_send_notification(todo.allocated_to):
    send_notification(todo)
```

### Bulk Operation Suppression

```python
def bulk_assign_without_spam(assignments):
    """Bulk assign with single digest email"""
    frappe.flags.mute_emails = True
    
    assigned_users = {}
    
    # Create all assignments
    for assignment in assignments:
        from frappe.desk.form import assign_to
        assign_to.add(assignment)
        
        # Track per user
        user = assignment["assign_to"][0]
        if user not in assigned_users:
            assigned_users[user] = []
        assigned_users[user].append(assignment)
    
    frappe.flags.mute_emails = False
    
    # Send single digest email per user
    for user, user_assignments in assigned_users.items():
        send_digest_email(user, user_assignments)

def send_digest_email(user, assignments):
    """Send single email with all assignments"""
    message = f"<h2>You have {len(assignments)} new assignments</h2><ul>"
    
    for assignment in assignments:
        message += f"<li>{assignment['doctype']} {assignment['name']}: {assignment['description']}</li>"
    
    message += "</ul>"
    
    frappe.sendmail(
        recipients=[user],
        subject=f"New Assignments: {len(assignments)} tasks",
        message=message
    )
```

### Time-Based Suppression

```python
def is_business_hours():
    """Check if current time is business hours"""
    from frappe.utils import now_datetime
    
    now = now_datetime()
    hour = now.hour
    
    # 9 AM to 6 PM
    return 9 <= hour < 18

def assign_with_timing(doctype, name, user):
    """Only send notification during business hours"""
    from frappe.desk.form import assign_to
    
    # Suppress if outside business hours
    if not is_business_hours():
        frappe.flags.mute_emails = True
    
    assign_to.add({
        "assign_to": [user],
        "doctype": doctype,
        "name": name
    })
    
    if not is_business_hours():
        frappe.flags.mute_emails = False
```

### Notification Frequency Control

```python
def check_notification_frequency(user):
    """Limit notification frequency"""
    # Get recent notifications
    recent_count = frappe.db.count("Notification Log", {
        "for_user": user,
        "type": "Assignment",
        "creation": [">=", frappe.utils.add_to_date(frappe.utils.now(), hours=-1)]
    })
    
    # Limit to 10 per hour
    return recent_count < 10

def rate_limited_notification(todo):
    """Send notification with rate limiting"""
    if check_notification_frequency(todo.allocated_to):
        send_notification(todo)
    else:
        # Queue for batch send later
        queue_notification(todo)
```

### Custom Notification Channels

```python
class NotificationManager:
    """Manage different notification channels"""
    
    @staticmethod
    def send_assignment_notification(todo, channels=None):
        """Send via multiple channels"""
        if channels is None:
            channels = ["email", "push"]
        
        for channel in channels:
            if channel == "email":
                NotificationManager.send_email(todo)
            elif channel == "sms":
                NotificationManager.send_sms(todo)
            elif channel == "push":
                NotificationManager.send_push(todo)
            elif channel == "slack":
                NotificationManager.send_slack(todo)
    
    @staticmethod
    def send_email(todo):
        """Send email notification"""
        frappe.sendmail(
            recipients=[todo.allocated_to],
            subject=f"New Assignment: {todo.description}",
            message=build_email_content(todo)
        )
    
    @staticmethod
    def send_sms(todo):
        """Send SMS notification"""
        phone = frappe.db.get_value("User", todo.allocated_to, "mobile_no")
        if phone:
            send_sms_message(phone, f"New task: {todo.description}")
    
    @staticmethod
    def send_push(todo):
        """Send push notification"""
        # Implement push notification logic
        pass
    
    @staticmethod
    def send_slack(todo):
        """Send Slack notification"""
        # Implement Slack notification logic
        pass

# Usage
NotificationManager.send_assignment_notification(
    todo,
    channels=["email", "slack"]
)
```
