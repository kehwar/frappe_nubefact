---
name: kehwar-frappe-test-runner
description: Comprehensive guide for running Frappe/ERPNext tests using bench run-tests command. Use when users ask about running tests, testing specific files, test modules, doctypes, or understanding test command options and filters.
---

# Frappe Test Runner

## Overview

This skill provides comprehensive guidance for running Python unit tests in Frappe/ERPNext applications using the `bench run-tests` command. It covers all test execution modes, from running entire app test suites to executing specific test methods.

## Command Syntax

```bash
bench run-tests [OPTIONS]
```

All commands assume execution from the bench directory: `/workspace/development/frappe-bench`

## Test Execution Modes

### 1. Run All Tests for an App

Run the entire test suite for an application:

```bash
bench run-tests --app soldamundo
bench run-tests --app erpnext
bench run-tests --app frappe
```

### 2. Run Tests for a Specific DocType

Run all tests associated with a DocType:

```bash
bench run-tests --app soldamundo --doctype "Sales Commission Period"
bench run-tests --app erpnext --doctype "Sales Invoice"
```

**Note**: DocType name should be in Title Case with spaces.

### 3. Run a Specific Test File/Module

Run tests from a specific Python test file. Supports both dotted module paths and file paths:

**Dotted module path** (traditional):
```bash
bench run-tests --module soldamundo.soldamundo.doctype.sales_commission_period.test_sales_commission_period
```

**File path** (convenient):
```bash
bench run-tests --module soldamundo/soldamundo/doctype/sales_commission_period/test_sales_commission_period
bench run-tests --module soldamundo/soldamundo/doctype/sales_commission_period/test_sales_commission_period.py
```

**Cross-app examples**:
```bash
bench run-tests --module erpnext.accounts.doctype.payment_entry.test_payment_entry
bench run-tests --module tweaks/tweaks/doctype/sync_job_type/test_sync_job_type.py
```

### 4. Run a Specific Test Class

Run all test methods within a specific test class:

```bash
bench run-tests --module soldamundo.soldamundo.doctype.sales_commission_period.test_sales_commission_period --case TestSalesCommissionPeriod
```

### 5. Run Specific Test Methods

Run one or more specific test methods. Can specify multiple `--test` flags:

```bash
bench run-tests --module soldamundo.soldamundo.doctype.sales_commission_period.test_sales_commission_period --test test_period_creation

# Multiple specific tests
bench run-tests --module soldamundo.tests.test_commissions --test test_rule_evaluation --test test_goal_calculation
```

### 6. Run Tests for All DocTypes in a Module

Run tests for all DocTypes within a specific Frappe module:

```bash
bench run-tests --module-def "Commissions"
bench run-tests --module-def "Accounts"
```

## Useful Options and Flags

### Common Flags

```bash
--verbose                  # Show detailed test output
--failfast                 # Stop on first test failure
--profile                  # Profile test execution
--coverage                 # Generate code coverage report
--skip-test-records        # Don't create test records
--skip-before-tests        # Skip before_tests hooks
```

### Combined Examples

```bash
# Run specific test file with verbose output and stop on first failure
bench run-tests --module soldamundo/soldamundo/doctype/sales_commission_period/test_sales_commission_period --verbose --failfast

# Run DocType tests with coverage
bench run-tests --app soldamundo --doctype "Sales Commission Period" --coverage

# Run specific test method with profiling
bench run-tests --module soldamundo.tests.test_sync --test test_item_sync --profile --verbose
```

### Output Options

```bash
--junit-xml-output <path>  # Generate JUnit XML report for CI/CD
```

Example:
```bash
bench run-tests --app soldamundo --junit-xml-output test-results.xml
```

## Understanding Test Paths

### Path Conversion

The test runner automatically converts file paths to Python module paths:

| Input Format | Converted To |
|-------------|--------------|
| `soldamundo/soldamundo/doctype/item/test_item.py` | `soldamundo.soldamundo.doctype.item.test_item` |
| `soldamundo/soldamundo/doctype/item/test_item` | `soldamundo.soldamundo.doctype.item.test_item` |

### Common Path Patterns

**DocType tests**:
- Pattern: `<app>/<app>/doctype/<doctype_name>/test_<doctype_name>.py`
- Example: `soldamundo/soldamundo/doctype/sales_commission_period/test_sales_commission_period.py`

**Module-level tests**:
- Pattern: `<app>/<app>/tests/test_<feature>.py`
- Example: `soldamundo/soldamundo/tests/test_commissions.py`

**Custom location tests**:
- Pattern: `<app>/<app>/<path>/test_<name>.py`
- Example: `tweaks/tweaks/custom/utils/test_helpers.py`

## Test Discovery

When using `--app`, the test runner:
1. Walks through the entire app directory
2. Finds all `test_*.py` files
3. Loads test classes that inherit from `unittest.TestCase`
4. Executes all test methods (those starting with `test_`)

## Site Configuration

Tests are disabled by default. To enable testing on a site:

```bash
bench --site development.localhost set-config allow_tests true
```

To check if tests are enabled:
```bash
bench --site development.localhost get-config allow_tests
```

## Test Dependencies

Test files can specify dependencies using the `test_dependencies` variable:

```python
# In test_sales_commission_period.py
test_dependencies = ["Item", "Customer", "Sales Person"]
```

The test runner will automatically create test records for these DocTypes before running tests.

## Tips and Best Practices

### 1. Use File Paths for Convenience

When working in VS Code or terminal, use file paths instead of dotted paths:
```bash
# Easier to type/copy
bench run-tests --module soldamundo/soldamundo/doctype/item/test_item.py

# vs the traditional way
bench run-tests --module soldamundo.soldamundo.doctype.item.test_item
```

### 2. Use --failfast for Development

Stop on first failure to quickly identify issues:
```bash
bench run-tests --module <path> --failfast
```

### 3. Use --verbose for Debugging

See detailed output including print statements:
```bash
bench run-tests --module <path> --verbose
```

### 4. Combine --doctype with --test

Run specific test method for a DocType:
```bash
bench run-tests --app soldamundo --doctype "Sales Commission Period" --test test_period_creation
```

### 5. Quick Test Iteration

For rapid test-driven development:
```bash
# Run single test file with verbose output and fail fast
bench run-tests --module <path> -v --failfast

# Short test feedback loop
watch -n 2 'bench run-tests --module <path> --test <method> --failfast'
```

## CI/CD Integration

For continuous integration:

```bash
# Run all app tests with JUnit output
bench run-tests --app soldamundo --junit-xml-output test-results.xml

# Run with coverage
bench run-tests --app soldamundo --coverage --junit-xml-output test-results.xml
```

## Implementation Details

### Command Definition
- File: `frappe/commands/utils.py`
- Function: `run_tests()` (line ~732)
- Handles CLI argument parsing and calls test runner

### Test Execution
- File: `frappe/test_runner.py`
- Function: `main()` (line ~40)
- Converts file paths to module paths (line ~103)
- Routes to appropriate test execution function

### Test Filtering
- File: `frappe/test_runner.py`
- Function: `_run_unittest()` (line ~260)
- Filters test cases by method name when `--test` is specified

## Troubleshooting

### "Testing is disabled for the site"

**Solution**: Enable tests on the site:
```bash
bench --site development.localhost set-config allow_tests true
```

### "ModuleNotFoundError" or "ImportError"

**Possible causes**:
- Incorrect module path
- App not installed on site
- Test file doesn't exist

**Solution**: Verify the file exists and use file path format:
```bash
ls soldamundo/soldamundo/doctype/sales_commission_period/test_sales_commission_period.py
bench run-tests --module soldamundo/soldamundo/doctype/sales_commission_period/test_sales_commission_period.py
```

### Tests Running but No Output

**Solution**: Use `--verbose` flag:
```bash
bench run-tests --module <path> --verbose
```

### Tests Fail Due to Missing Test Records

**Possible causes**:
- Test dependencies not declared
- `--skip-test-records` flag used

**Solution**: Ensure test dependencies are declared in test file:
```python
test_dependencies = ["Item", "Customer"]
```

Or remove the `--skip-test-records` flag if used.

## Quick Reference

```bash
# Run all app tests
bench run-tests --app <app_name>

# Run DocType tests
bench run-tests --app <app_name> --doctype "<DocType Name>"

# Run specific test file (recommended)
bench run-tests --module <app>/<path>/test_<name>.py

# Run specific test method
bench run-tests --module <path> --test <method_name>

# Development mode
bench run-tests --module <path> --verbose --failfast

# CI mode
bench run-tests --app <app> --junit-xml-output results.xml
```

## Related Skills

- **kehwar-frappe-frappe-tests-expert**: For writing tests
- **kehwar-frappe-bench-commands**: For other bench commands
- **kehwar-frappe-frappe-ci-expert**: For CI/CD test setup
