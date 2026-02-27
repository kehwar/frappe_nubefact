# Frappe Test Patterns Reference

## Test Base Classes

### FrappeTestCase

All tests inherit from `frappe.tests.utils.FrappeTestCase` (which extends `unittest.TestCase`).

```python
from frappe.tests.utils import FrappeTestCase

class TestMyFeature(FrappeTestCase):
    pass
```

**Key features:**
- Auto-rollback after each test class (changes don't persist)
- Access to custom Frappe assertions
- Built-in context managers for common operations
- Transaction management

### MockedRequestTestCase

For tests that need HTTP request mocking:

```python
from frappe.tests.utils import MockedRequestTestCase

class TestAPI(MockedRequestTestCase):
    def setUp(self):
        super().setUp()
        # self.responses is available for mocking
```

## Setup and Teardown

### Class-level Setup

Use `setUpClass` for one-time setup before all tests in a class:

```python
@classmethod
def setUpClass(cls):
    super().setUpClass()  # ALWAYS call super()
    make_test_records("User")
    # One-time setup
```

**Critical:** Always call `super().setUpClass()` or tests will break.

### Instance-level Setup

Use `setUp` for setup before each test method:

```python
def setUp(self):
    frappe.set_user("Administrator")
    frappe.db.delete("My DocType")
```

### Teardown

Use `tearDown` for cleanup after each test:

```python
def tearDown(self):
    frappe.set_user("Administrator")
    # Cleanup actions
```

Use `addCleanup` for guaranteed cleanup:

```python
def test_something(self):
    self.addCleanup(lambda: frappe.db.rollback())
    # Test code
```

### Enabling Server Scripts

For tests that need to execute server scripts or use safe exec functionality:

```python
@classmethod
def setUpClass(cls):
    super().setUpClass()  # ALWAYS call super()
    cls.enable_safe_exec()  # Enable server script execution
```

**Use cases:**
- Testing Script Reports (reports with custom Python code)
- Testing Server Scripts
- Testing custom permission queries with server-side scripts
- Any functionality requiring `safe_exec`

**How it works:**
- Enables `server_script_enabled` in site config
- Automatically disables it after test class completes via `addClassCleanup`
- Prevents server scripts from running in other tests

**Example:**

```python
from frappe.tests.utils import FrappeTestCase

class TestScriptReport(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.enable_safe_exec()
    
    def test_report_execution(self):
        # Server scripts can now execute
        result = frappe.get_doc("Report", "Script Report").execute()
        self.assertTrue(result)
```

## Test Dependencies and Fixtures

### Declaring Dependencies

Use `test_dependencies` list to specify required test data:

```python
test_dependencies = ["User", "Blogger", "Blog Post"]
```

### Using make_test_records

Load test records for a doctype:

```python
from frappe.test_runner import make_test_records

make_test_records("User")
```

### Creating test_records.json

Place in doctype directory:

```json
[
    {
        "doctype": "Contact",
        "first_name": "_Test Contact",
        "email_ids": [
            {
                "email_id": "test@example.com",
                "is_primary": 1
            }
        ]
    }
]
```

## Database and Transactions

### Auto-Rollback

By default, database changes rollback after each test class.

### Explicit Commit

When you need changes to persist across tests:

```python
frappe.db.commit()
```

### Savepoints

For nested transactions:

```python
from frappe.database import savepoint

try:
    savepoint = "my_savepoint"
    frappe.db.savepoint(savepoint)
    # Operations
except Exception:
    frappe.db.rollback(save_point=savepoint)
```

## User Context Management

### Setting User

```python
frappe.set_user("test@example.com")
```

### Context Manager

```python
with self.set_user("test@example.com"):
    # Code runs as this user
    pass
# User automatically restored
```

## Database Connections

### Primary and Secondary Connections

Simulate multiple users:

```python
with self.primary_connection():
    # Actions as first user
    pass

with self.secondary_connection():
    # Actions as second user
    pass
```

## Mocking and Patching

### Using unittest.mock

```python
from unittest.mock import patch, Mock

@patch("frappe.attach_print", return_value={})
def test_something(self, mock_attach):
    # mock_attach is available
    pass
```

### Patcher Pattern

```python
def setUp(self):
    self.patcher = patch("frappe.attach_print", return_value={})
    self.patcher.start()

def tearDown(self):
    self.patcher.stop()
```

## Custom Assertions

### assertDocumentEqual

Compare documents with automatic field type handling:

```python
expected = {"doctype": "ToDo", "description": "Test"}
self.assertDocumentEqual(expected, actual_doc)
```

### assertQueryEqual

Compare SQL queries (normalized):

```python
self.assertQueryEqual(expected_query, actual_query)
```

### assertQueryCount

Assert maximum number of queries:

```python
with self.assertQueryCount(5):
    # Code that executes queries
    pass
```

### assertRedisCallCounts

Assert maximum Redis operations:

```python
with self.assertRedisCallCounts(10):
    # Code that uses cache
    pass
```

### assertRowsRead

Assert maximum rows read from database:

```python
with self.assertRowsRead(100):
    # Database operations
    pass
```

### assertSequenceSubset

Assert one sequence is subset of another:

```python
self.assertSequenceSubset(larger_list, smaller_list)
```

## Context Managers

### change_settings

Temporarily change document settings:

```python
from frappe.tests.utils import change_settings

@change_settings("System Settings", enable_password_policy=1)
def test_password_policy(self):
    # Settings changed for this test
    pass

# Or as context manager:
with change_settings("System Settings", enable_password_policy=1):
    # Code here
    pass
```

### freeze_time

Mock datetime:

```python
with self.freeze_time("2024-01-01 10:00:00"):
    # Time is frozen
    pass
```

### switch_site

Switch to different site:

```python
with self.switch_site("other_site"):
    # Working on different site
    pass
```

## Test Naming Conventions

- Test files: `test_<feature>.py`
- Test classes: `Test<Feature>`
- Test methods: `test_<specific_behavior>`
- Test doctypes: Prefix with `_Test` (e.g., `_Test Customer`)
- Test records: Use descriptive names with test prefix

## Common Patterns

### Creating Test Documents

```python
doc = frappe.get_doc({
    "doctype": "Event",
    "subject": "test-event",
    "starts_on": "2024-01-01",
    "event_type": "Public"
})
doc.insert()
```

### Helper Functions

Create helper functions at module level:

```python
def create_test_contact(name, email):
    return frappe.get_doc({
        "doctype": "Contact",
        "first_name": name,
        "email_ids": [{"email_id": email}]
    }).insert()

class TestContact(FrappeTestCase):
    def test_contact_creation(self):
        contact = create_test_contact("Test", "test@example.com")
        self.assertEqual(contact.first_name, "Test")
```

### Testing Permissions

```python
def test_permission(self):
    frappe.set_user("test@example.com")
    doc = frappe.get_doc("Blog Post", "my-post")
    self.assertTrue(doc.has_permission("read"))
    self.assertFalse(doc.has_permission("write"))
```

### Testing Workflows

```python
from frappe.model.workflow import apply_workflow

def test_workflow(self):
    doc = create_test_doc()
    self.assertEqual(doc.workflow_state, "Pending")
    
    apply_workflow(doc, "Approve")
    self.assertEqual(doc.workflow_state, "Approved")
```

### Testing Exceptions

```python
def test_validation_error(self):
    self.assertRaises(
        frappe.ValidationError,
        create_invalid_doc
    )
```

### Conditional Test Execution

```python
from frappe.tests.test_query_builder import run_only_if, db_type_is

@run_only_if(db_type_is.MARIADB)
def test_mariadb_specific(self):
    # Only runs on MariaDB
    pass
```

## Performance Testing

### Timeout Decorator

```python
from frappe.tests.utils import timeout

@timeout(seconds=5)
def test_fast_operation(self):
    # Must complete in 5 seconds
    pass
```

## Best Practices

1. **Always call super() in setUpClass** - Framework setup happens there
2. **Use addCleanup for guaranteed cleanup** - Runs even if test fails
3. **Avoid commits unless necessary** - Let auto-rollback work
4. **Clear caches when testing cached data** - `frappe.clear_cache(doctype="X")`
5. **Use meaningful test data names** - Prefix with `_Test` or descriptive names
6. **Test one thing per test method** - Keep tests focused
7. **Use helper functions for repeated setup** - Keep tests DRY
8. **Mock external services** - Don't make real API calls
9. **Test both success and failure cases** - Don't just test happy path
10. **Use appropriate assertions** - Use Frappe's custom assertions when available
