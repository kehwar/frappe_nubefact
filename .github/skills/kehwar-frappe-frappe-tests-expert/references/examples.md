# Frappe Test Examples

This document provides complete, working examples of common test scenarios in Frappe.

## Basic DocType Test

```python
# frappe/contacts/doctype/contact/test_contact.py
from frappe.tests.utils import FrappeTestCase
import frappe

test_dependencies = ["Contact", "Salutation"]

class TestContact(FrappeTestCase):
    def test_check_default_email(self):
        emails = [
            {"email": "test1@example.com", "is_primary": 0},
            {"email": "test2@example.com", "is_primary": 1},
        ]
        contact = create_contact("Test User", "Mr", emails=emails)
        self.assertEqual(contact.email_id, "test2@example.com")
    
    def test_full_name_generation(self):
        contact = frappe.get_doc({
            "doctype": "Contact",
            "first_name": "John",
            "last_name": "Doe",
            "salutation": "Mr"
        }).insert()
        
        self.assertEqual(contact.get_full_name(), "Mr John Doe")

def create_contact(name, salutation, emails=None):
    doc = frappe.get_doc({
        "doctype": "Contact",
        "first_name": name,
        "salutation": salutation
    })
    
    if emails:
        for email in emails:
            doc.add_email(email.get("email"), email.get("is_primary"))
    
    doc.insert()
    return doc
```

## Test with Setup and Teardown

```python
from frappe.tests.utils import FrappeTestCase
import frappe

class TestWorkflow(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from frappe.test_runner import make_test_records
        make_test_records("User")
    
    def setUp(self):
        # Runs before each test
        frappe.db.delete("Workflow Action")
        self.workflow = self.create_test_workflow()
    
    def tearDown(self):
        # Runs after each test
        frappe.set_user("Administrator")
        if frappe.db.exists("Workflow", "Test Workflow"):
            frappe.delete_doc("Workflow", "Test Workflow")
    
    def test_workflow_transition(self):
        doc = self.create_test_doc()
        self.assertEqual(doc.workflow_state, "Draft")
        
        from frappe.model.workflow import apply_workflow
        apply_workflow(doc, "Approve")
        
        self.assertEqual(doc.workflow_state, "Approved")
    
    def create_test_workflow(self):
        # Helper method
        return frappe.get_doc({
            "doctype": "Workflow",
            "name": "Test Workflow",
            "document_type": "ToDo"
        }).insert()
    
    def create_test_doc(self):
        return frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo"
        }).insert()
```

## Database Query Test

```python
from frappe.tests.utils import FrappeTestCase
import frappe

class TestDB(FrappeTestCase):
    def test_get_value(self):
        # Test basic get_value
        result = frappe.db.get_value("User", {"name": ["=", "Administrator"]})
        self.assertEqual(result, "Administrator")
        
        # Test with filters
        result = frappe.db.get_value("User", {"name": ["like", "Admin%"]})
        self.assertEqual(result, "Administrator")
    
    def test_query_count(self):
        # Ensure code doesn't make too many queries
        with self.assertQueryCount(3):
            users = frappe.get_all("User", limit=10)
            for user in users:
                frappe.db.get_value("User", user.name, "email")
```

## Permission Test

```python
from frappe.tests.utils import FrappeTestCase
import frappe
from frappe.permissions import add_permission, update_permission_property

class TestPermissions(FrappeTestCase):
    def setUp(self):
        frappe.clear_cache(doctype="Blog Post")
        frappe.db.delete("User Permission")
        frappe.set_user("test@example.com")
    
    def tearDown(self):
        frappe.set_user("Administrator")
    
    def test_basic_permission(self):
        post = frappe.get_doc("Blog Post", "test-post")
        self.assertTrue(post.has_permission("read"))
    
    def test_user_permission(self):
        # Add user permission
        from frappe.permissions import add_user_permission
        add_user_permission("Blog Category", "Tech", "test@example.com")
        
        # User should only see posts in Tech category
        posts = frappe.get_all("Blog Post", filters={"blog_category": "Tech"})
        self.assertTrue(len(posts) > 0)
        
        # Should not see posts in other categories
        other_posts = frappe.get_all("Blog Post", filters={"blog_category": "News"})
        self.assertEqual(len(other_posts), 0)
```

## User Context Test

```python
from frappe.tests.utils import FrappeTestCase
import frappe

class TestUserContext(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test users
        if not frappe.db.exists("User", "test1@example.com"):
            user = frappe.get_doc({
                "doctype": "User",
                "email": "test1@example.com",
                "first_name": "Test1"
            }).insert()
            user.add_roles("Blogger")
    
    def test_with_different_user(self):
        # Using context manager
        with self.set_user("test1@example.com"):
            # Code runs as test1
            doc = frappe.get_doc({"doctype": "Note", "title": "Test"})
            doc.insert()
            self.assertEqual(doc.owner, "test1@example.com")
        
        # User automatically restored to Administrator
        self.assertEqual(frappe.session.user, "Administrator")
    
    def test_multiple_connections(self):
        # Simulate two users simultaneously
        with self.primary_connection():
            frappe.set_user("test1@example.com")
            doc1 = frappe.get_doc({"doctype": "Note", "title": "Doc1"})
            doc1.insert()
        
        with self.secondary_connection():
            frappe.set_user("test2@example.com")
            doc2 = frappe.get_doc({"doctype": "Note", "title": "Doc2"})
            doc2.insert()
```

## Mocking Test

```python
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, Mock
import frappe

class TestEmailSending(FrappeTestCase):
    @patch("frappe.sendmail")
    def test_email_notification(self, mock_sendmail):
        # sendmail is mocked
        doc = frappe.get_doc({
            "doctype": "Communication",
            "subject": "Test Email",
            "recipients": "test@example.com"
        })
        doc.insert()
        
        # Verify sendmail was called
        mock_sendmail.assert_called_once()
    
    def test_with_patcher(self):
        patcher = patch("frappe.get_hooks", return_value=["custom_hook"])
        patcher.start()
        self.addCleanup(patcher.stop)
        
        # Test code using mocked get_hooks
        hooks = frappe.get_hooks("my_hook")
        self.assertEqual(hooks, ["custom_hook"])
```

## Settings Change Test

```python
from frappe.tests.utils import FrappeTestCase, change_settings
import frappe

class TestSystemSettings(FrappeTestCase):
    @change_settings("System Settings", enable_password_policy=1)
    def test_with_password_policy_enabled(self):
        # System Settings temporarily changed
        settings = frappe.get_doc("System Settings")
        self.assertEqual(settings.enable_password_policy, 1)
        
        # Test password validation
        # ...
    
    def test_with_context_manager(self):
        with change_settings("System Settings", enable_password_policy=1):
            # Settings changed here
            self.assertTrue(frappe.get_single("System Settings").enable_password_policy)
        
        # Settings restored here
```

## Time-based Test

```python
from frappe.tests.utils import FrappeTestCase
import frappe
from frappe.utils import now_datetime, add_days

class TestTimeDependent(FrappeTestCase):
    def test_with_frozen_time(self):
        freeze_time = "2024-01-01 10:00:00"
        
        with self.freeze_time(freeze_time):
            # Time is frozen
            doc = frappe.get_doc({
                "doctype": "Event",
                "subject": "Test Event",
                "starts_on": now_datetime()
            }).insert()
            
            self.assertEqual(str(doc.starts_on), "2024-01-01 10:00:00")
```

## Exception Testing

```python
from frappe.tests.utils import FrappeTestCase
import frappe

class TestValidations(FrappeTestCase):
    def test_validation_error(self):
        # Test that validation error is raised
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc({
                "doctype": "User",
                "email": "invalid-email"  # Invalid format
            })
            doc.insert()
    
    def test_mandatory_field(self):
        # Test mandatory field validation
        self.assertRaises(
            frappe.MandatoryError,
            lambda: frappe.get_doc({"doctype": "User"}).insert()
        )
    
    def test_duplicate_entry(self):
        # Create first doc
        frappe.get_doc({
            "doctype": "User",
            "email": "duplicate@example.com",
            "first_name": "Test"
        }).insert()
        
        # Try to create duplicate
        with self.assertRaises(frappe.DuplicateEntryError):
            frappe.get_doc({
                "doctype": "User",
                "email": "duplicate@example.com",
                "first_name": "Test2"
            }).insert()
```

## Custom DocType Test

```python
from frappe.tests.utils import FrappeTestCase
from frappe.core.doctype.doctype.test_doctype import new_doctype
import frappe

class TestCustomDocType(FrappeTestCase):
    def test_create_custom_doctype(self):
        # Create a custom doctype for testing
        doctype = new_doctype(
            fields=[
                {"label": "Title", "fieldname": "title", "fieldtype": "Data"},
                {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency"}
            ]
        ).insert()
        
        # Use the custom doctype
        doc = frappe.get_doc({
            "doctype": doctype.name,
            "title": "Test",
            "amount": 100.50
        }).insert()
        
        self.assertEqual(doc.amount, 100.50)
```

## Document Comparison Test

```python
from frappe.tests.utils import FrappeTestCase
import frappe

class TestDocumentComparison(FrappeTestCase):
    def test_document_equal(self):
        expected = {
            "doctype": "ToDo",
            "description": "Test ToDo",
            "status": "Open"
        }
        
        actual = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo",
            "status": "Open"
        }).insert()
        
        # assertDocumentEqual handles type conversions
        self.assertDocumentEqual(expected, actual)
    
    def test_with_child_tables(self):
        expected = {
            "doctype": "Event",
            "subject": "Test",
            "event_participants": [
                {"reference_doctype": "User", "reference_docname": "Administrator"}
            ]
        }
        
        actual = frappe.get_doc(expected).insert()
        self.assertDocumentEqual(expected, actual)
```

## API/Client Test

```python
from frappe.tests.utils import FrappeTestCase
import frappe
import json

class TestAPI(FrappeTestCase):
    def test_api_endpoint(self):
        # Set up request context
        frappe.set_user("Administrator")
        frappe.local.form_dict = frappe._dict({
            "doctype": "User",
            "name": "Administrator"
        })
        
        # Call API method
        result = frappe.client.get("User", "Administrator")
        
        self.assertEqual(result.get("name"), "Administrator")
    
    def test_get_list(self):
        result = frappe.client.get_list("User", fields=["name", "email"], limit=5)
        
        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 5)
```

## Cleanup Pattern Test

```python
from frappe.tests.utils import FrappeTestCase
import frappe

class TestWithCleanup(FrappeTestCase):
    def test_with_addCleanup(self):
        # Create test data
        doc = frappe.get_doc({
            "doctype": "Note",
            "title": "Test Note"
        }).insert()
        
        # Register cleanup - runs even if test fails
        self.addCleanup(lambda: frappe.delete_doc("Note", doc.name))
        
        # Test operations
        self.assertTrue(frappe.db.exists("Note", doc.name))
```

## Server Scripts / Safe Exec Test

```python
from frappe.tests.utils import FrappeTestCase
import frappe

class TestScriptReport(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Enable server script execution for this test class
        cls.enable_safe_exec()
    
    def test_script_report_execution(self):
        # Create a script report for testing
        report = frappe.get_doc({
            "doctype": "Report",
            "ref_doctype": "User",
            "report_name": "Test Script Report",
            "report_type": "Script Report",
            "is_standard": "No",
            "module": "Custom",
            "query": "SELECT name, email FROM `tabUser`"
        }).insert()
        
        self.addCleanup(lambda: frappe.delete_doc("Report", report.name))
        
        # Execute the report - requires safe_exec to be enabled
        columns, data = report.execute_script()
        
        self.assertTrue(len(columns) > 0)
        self.assertTrue(len(data) > 0)
    
    def test_server_script(self):
        # Test server script execution
        from frappe.utils.safe_exec import safe_exec
        
        _locals = {"result": None}
        safe_exec('result = frappe.utils.cint("42")', None, _locals)
        
        self.assertEqual(_locals["result"], 42)
```

## Report Test

```python
from frappe.tests.utils import FrappeTestCase
import frappe

class TestReport(FrappeTestCase):
    def test_report_execution(self):
        # Execute a report
        result = frappe.get_doc("Report", "User Report").execute_script()
        
        self.assertIsInstance(result, tuple)
        columns, data = result
        
        self.assertTrue(len(columns) > 0)
        self.assertTrue(len(data) > 0)
```
