app_name = "nubefact"
app_title = "Nubefact"
app_publisher = "Erick W.R."
app_description = "Integration with Nubefact API"
app_email = "erickkwr@gmail.com"
app_license = "mit"

safe_exec_globals = ["nubefact.utils.safe_exec.safe_exec_globals"]
# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "nubefact",
# 		"logo": "/assets/nubefact/logo.png",
# 		"title": "Nubefact",
# 		"route": "/nubefact",
# 		"has_permission": "nubefact.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/nubefact/css/nubefact.css"
app_include_js = "nubefact.bundle.js"

# include js, css files in header of web template
# web_include_css = "/assets/nubefact/css/nubefact.css"
# web_include_js = "/assets/nubefact/js/nubefact.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "nubefact/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "nubefact/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "nubefact.utils.jinja_methods",
# 	"filters": "nubefact.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "nubefact.install.before_install"
# after_install = "nubefact.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "nubefact.uninstall.before_uninstall"
# after_uninstall = "nubefact.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "nubefact.utils.before_app_install"
# after_app_install = "nubefact.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "nubefact.utils.before_app_uninstall"
# after_app_uninstall = "nubefact.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "nubefact.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"nubefact.tasks.all"
# 	],
# 	"daily": [
# 		"nubefact.tasks.daily"
# 	],
# 	"hourly": [
# 		"nubefact.tasks.hourly"
# 	],
# 	"weekly": [
# 		"nubefact.tasks.weekly"
# 	],
# 	"monthly": [
# 		"nubefact.tasks.monthly"
# 	],
# }

scheduler_events = {
    "cron": {
        "*/5 * * * *": [
            "nubefact.nubefact.doctype.nubefact_guia_de_remision.nubefact_guia_de_remision.consultar_guias_pendientes",
            "nubefact.nubefact.doctype.nubefact_facturacion.nubefact_facturacion.poll_pending_invoices",
        ]
    }
}

# Testing
# -------

# before_tests = "nubefact.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "nubefact.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "nubefact.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

ignore_links_on_delete = ["Nubefact API Log"]

# Request Events
# ----------------
# before_request = ["nubefact.utils.before_request"]
# after_request = ["nubefact.utils.after_request"]

# Job Events
# ----------
# before_job = ["nubefact.utils.before_job"]
# after_job = ["nubefact.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"nubefact.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
