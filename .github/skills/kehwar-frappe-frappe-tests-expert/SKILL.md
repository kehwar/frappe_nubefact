---
name: kehwar-frappe-frappe-tests-expert
description: Expert guidance on writing tests for Frappe framework applications including test structure, setup/teardown patterns, FrappeTestCase usage, fixtures, database transactions, user context management, mocking, custom assertions, and best practices. Use when creating new tests, debugging test failures, understanding test patterns, working with test fixtures, setting up test data, testing permissions, workflows, or any testing-related tasks in Frappe or ERPNext applications.
---

# Frappe Tests Expert

Expert guidance for writing tests in the Frappe framework, covering test structure, patterns, and best practices specific to Frappe's testing infrastructure.

## Quick Start

All Frappe tests inherit from `FrappeTestCase`:

```python
from frappe.tests.utils import FrappeTestCase
import frappe

test_dependencies = ["User"]  # Loads test fixtures

class TestMyFeature(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()  # REQUIRED: Always call super()
        # One-time setup

    def test_basic_functionality(self):
        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo"
        }).insert()

        self.assertEqual(doc.docstatus, 0)
```

## Core Concepts

### 1. FrappeTestCase Base Class

All tests inherit from `frappe.tests.utils.FrappeTestCase` which extends `unittest.TestCase`.

**Key features:**
- Automatic transaction rollback after each test class
- Custom Frappe-specific assertions
- Built-in context managers for user switching, settings changes, time freezing
- Database connection management

**Critical rule:** Always call `super().setUpClass()` in your `setUpClass` method or tests will break.

### 2. Test Files and Naming

- **Test files:** `test_<feature>.py` (e.g., `test_workflow.py`)
- **Test classes:** `Test<Feature>` (e.g., `TestWorkflow`)
- **Test methods:** `test_<specific_behavior>` (e.g., `test_approve_transition`)
- **Test data:** Prefix with `_Test` (e.g., `_Test Customer`, `_Test User`)

### 3. Transaction Management

**Default behavior:** All database changes are automatically rolled back after each test class completes. This keeps tests isolated.

**When you need persistence:**
```python
frappe.db.commit()  # Explicitly commit changes
```

**Savepoints for nested transactions:**
```python
from frappe.database import savepoint

try:
    frappe.db.savepoint("my_savepoint")
    # Operations
except Exception:
    frappe.db.rollback(save_point="my_savepoint")
```

### 4. Test Dependencies and Fixtures

Declare dependencies to load test data:

```python
test_dependencies = ["User", "Blogger", "Blog Post"]
```

**Loading test records:**
```python
from frappe.test_runner import make_test_records
make_test_records("User")  # Loads from test_records.json
```

**Creating test_records.json:**

Place in your doctype folder (e.g., `contacts/doctype/contact/test_records.json`):

```json
[
    {
        "doctype": "Contact",
        "first_name": "_Test Contact",
        "email_ids": [
            {"email_id": "test@example.com", "is_primary": 1}
        ]
    }
]
```

## Test Structure Patterns

### Setup and Teardown

```python
class TestWorkflow(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        """One-time setup before all tests in this class"""
        super().setUpClass()  # REQUIRED
        make_test_records("User")

    def setUp(self):
        """Setup before each test method"""
        frappe.set_user("Administrator")
        frappe.db.delete("Workflow Action")

    def tearDown(self):
        """Cleanup after each test method"""
        frappe.set_user("Administrator")

    def test_something(self):
        # Use addCleanup for guaranteed cleanup
        self.addCleanup(lambda: frappe.delete_doc("Note", "test-note"))
        # Test code
```

### Enabling Server Scripts

When tests need to execute server scripts or use safe exec functionality (e.g., for testing reports with script, custom permissions, or server scripts), enable it in `setUpClass`:

```python
class TestQueryReport(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()  # REQUIRED
        cls.enable_safe_exec()  # Enable server script execution

    def test_script_report(self):
        # Now server scripts can be executed
        result = frappe.get_doc("Report", "My Script Report").execute()
```

**When to use:**
- Testing Script Reports (reports with custom Python code)
- Testing Server Scripts
- Testing custom permission queries with scripts
- Any test that requires `safe_exec` functionality

**Note:** `enable_safe_exec()` automatically disables server scripts after the test class completes via `addClassCleanup`.

### Helper Functions

Create module-level helper functions for reusable test setup:

```python
def create_test_contact(name, email):
    """Helper to create test contact"""
    return frappe.get_doc({
        "doctype": "Contact",
        "first_name": name,
        "email_ids": [{"email_id": email, "is_primary": 1}]
    }).insert()

class TestContact(FrappeTestCase):
    def test_contact_creation(self):
        contact = create_test_contact("Test", "test@example.com")
        self.assertEqual(contact.first_name, "Test")
```

## User Context Management

### Basic User Switching

```python
frappe.set_user("test@example.com")
# Operations as this user
frappe.set_user("Administrator")  # Reset
```

### Context Manager (Recommended)

```python
with self.set_user("test@example.com"):
    # Code runs as test@example.com
    doc.insert()
# User automatically restored
```

### Multiple Connections (Simulating Concurrent Users)

```python
with self.primary_connection():
    frappe.set_user("user1@example.com")
    doc1.insert()

with self.secondary_connection():
    frappe.set_user("user2@example.com")
    doc2.insert()
```

## Custom Assertions

Frappe provides specialized assertions for common testing needs:

### assertDocumentEqual

Compares documents with automatic type handling (handles floats, dates, ints):

```python
expected = {"doctype": "ToDo", "description": "Test", "priority": 1}
self.assertDocumentEqual(expected, actual_doc)
```

### assertQueryEqual

Compares SQL queries with normalization:

```python
self.assertQueryEqual(expected_sql, actual_sql)
```

### assertQueryCount

Ensures code doesn't execute too many queries:

```python
with self.assertQueryCount(5):
    # Code that should make at most 5 queries
    frappe.get_all("User", limit=10)
```

### assertRedisCallCounts

Monitors cache operations:

```python
with self.assertRedisCallCounts(10):
    # Code using cache
    pass
```

### assertRowsRead

Monitors rows read from database:

```python
with self.assertRowsRead(100):
    # Database reads
    pass
```

### assertSequenceSubset

```python
self.assertSequenceSubset(larger_list, smaller_list)
```

## Context Managers

### change_settings

Temporarily modify document settings:

```python
from frappe.tests.utils import change_settings

# As decorator
@change_settings("System Settings", enable_password_policy=1)
def test_password_policy(self):
    # Settings changed for this test
    pass

# As context manager
with change_settings("System Settings", enable_password_policy=1):
    # Settings changed here
    pass
```

### freeze_time

Mock datetime for time-dependent tests:

```python
with self.freeze_time("2024-01-01 10:00:00"):
    # Time is frozen
    doc = create_event()
    self.assertEqual(str(doc.starts_on), "2024-01-01 10:00:00")
```

### switch_site

Test multi-site scenarios:

```python
with self.switch_site("other_site"):
    # Operations on different site
    pass
```

## Mocking

### Using unittest.mock

```python
from unittest.mock import patch, Mock

@patch("frappe.sendmail")
def test_email_sending(self, mock_sendmail):
    send_notification()
    mock_sendmail.assert_called_once()
```

### Patcher Pattern

```python
def setUp(self):
    self.patcher = patch("frappe.attach_print", return_value={})
    self.patcher.start()
    self.addCleanup(self.patcher.stop)

def test_something(self):
    # Mocked function is active
    pass
```

### Mocking Hooks

```python
from frappe.tests.utils import patch_hooks

with patch_hooks({"my_hook": ["custom_handler"]}):
    # frappe.get_hooks("my_hook") returns ["custom_handler"]
    pass
```

## Testing Common Scenarios

### Testing Permissions

```python
def test_user_permission(self):
    frappe.set_user("test@example.com")
    doc = frappe.get_doc("Blog Post", "my-post")

    self.assertTrue(doc.has_permission("read"))
    self.assertFalse(doc.has_permission("write"))
```

### Testing Workflows

```python
from frappe.model.workflow import apply_workflow

def test_workflow_transition(self):
    doc = create_test_doc()
    self.assertEqual(doc.workflow_state, "Pending")

    apply_workflow(doc, "Approve")
    self.assertEqual(doc.workflow_state, "Approved")
```

### Testing Exceptions

```python
def test_validation_error(self):
    with self.assertRaises(frappe.ValidationError):
        invalid_doc = frappe.get_doc({
            "doctype": "User",
            "email": "invalid"
        })
        invalid_doc.insert()
```

### Testing API Endpoints

```python
def test_api_endpoint(self):
    frappe.set_user("Administrator")
    frappe.local.form_dict = frappe._dict({
        "doctype": "User",
        "name": "Administrator"
    })

    result = frappe.client.get("User", "Administrator")
    self.assertEqual(result.get("name"), "Administrator")
```

## Best Practices

1. **Always call super() in setUpClass** - Critical for framework initialization
2. **Use addCleanup for guaranteed cleanup** - Executes even if test fails
3. **Avoid unnecessary commits** - Let auto-rollback work
4. **Clear caches when needed** - `frappe.clear_cache(doctype="X")`
5. **Use descriptive test data names** - Prefix with `_Test` or meaningful names
6. **Test one behavior per test method** - Keep tests focused and isolated
7. **Use helper functions** - Extract common setup code
8. **Mock external services** - Never make real API calls in tests
9. **Test both success and failure cases** - Don't just test happy paths
10. **Use Frappe's custom assertions** - They handle type conversions correctly

## Common Pitfalls

- **Forgetting super().setUpClass()** - Tests will fail mysteriously
- **Not cleaning up test data** - Use `addCleanup` or `tearDown`
- **Committing unnecessarily** - Creates persistent test data
- **Not clearing caches** - Tests may pass locally but fail in CI
- **Testing with wrong user** - Remember to set user context
- **Hardcoding IDs** - Test data IDs may differ across environments

## Conditional Test Execution

Run tests only on specific database types:

```python
from frappe.tests.test_query_builder import run_only_if, db_type_is

@run_only_if(db_type_is.MARIADB)
def test_mariadb_specific(self):
    # Only runs on MariaDB
    pass

@run_only_if(db_type_is.POSTGRES)
def test_postgres_specific(self):
    # Only runs on PostgreSQL
    pass
```

## Performance Testing

```python
from frappe.tests.utils import timeout

@timeout(seconds=5)
def test_fast_operation(self):
    # Must complete within 5 seconds
    perform_operation()
```

## Reference Documentation

For detailed patterns and examples, see:

- **[references/test-patterns.md](references/test-patterns.md)** - Comprehensive test patterns reference including:
  - Detailed FrappeTestCase features
  - All custom assertions with examples
  - Context managers and their usage
  - Database transaction patterns
  - Mocking strategies
  - Best practices and common patterns

- **[references/examples.md](references/examples.md)** - Complete working examples including:
  - Basic DocType tests
  - Setup/teardown patterns
  - Permission testing
  - Workflow testing
  - API testing
  - Mocking examples
  - Time-based tests
  - Document comparison tests
