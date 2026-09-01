#!/usr/bin/env python3
"""Provision an idempotent Frappe Bench for the bind-mounted Nubefact app."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

BENCH_ROOT = Path(os.environ.get("BENCH_ROOT", "/workspace/development/frappe-bench"))
DEFAULT_APP_SOURCE = Path(__file__).resolve().parent.parent
APP_SOURCE = Path(os.environ.get("APP_SOURCE", DEFAULT_APP_SOURCE))
SITE_NAME = os.environ.get("SITE_NAME", "development.localhost")
APPS_JSON = APP_SOURCE / ".devcontainer" / "apps.json"
DB_HOST = os.environ.get("DB_HOST", "mariadb")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_ROOT_PASSWORD = os.environ.get("DB_ROOT_PASSWORD", "123")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")


def run(
	*args: str | Path,
	cwd: Path | None = None,
	hidden_values: tuple[str, ...] = (),
) -> None:
	command = [str(arg) for arg in args]
	printable = command.copy()
	for index, value in enumerate(printable):
		if value in hidden_values:
			printable[index] = "<redacted>"
	print(f"\n$ {' '.join(printable)}", flush=True)
	subprocess.run(command, cwd=cwd, check=True)


def load_apps() -> list[dict[str, Any]]:
	with APPS_JSON.open(encoding="utf-8") as apps_file:
		apps = json.load(apps_file)

	required_keys = {"app_name", "repository_directory", "url", "branch", "revision"}
	if not isinstance(apps, list):
		raise ValueError(f"{APPS_JSON} must contain a list of apps")
	for app in apps:
		missing = required_keys - app.keys()
		if missing:
			raise ValueError(f"Invalid app definition in {APPS_JSON}; missing {sorted(missing)}")
	if sum(app["app_name"] == "frappe" for app in apps) != 1:
		raise ValueError(f"{APPS_JSON} must define exactly one Frappe app")
	return apps


def load_framework_app() -> dict[str, Any]:
	return next(app for app in load_apps() if app["app_name"] == "frappe")


def load_dependency_apps() -> list[dict[str, Any]]:
	return [app for app in load_apps() if app["app_name"] != "frappe"]


def prepare_bench_mount() -> None:
	apps_directory = BENCH_ROOT / "apps"
	run("sudo", "mkdir", "-p", apps_directory)
	run("sudo", "chown", "frappe:frappe", BENCH_ROOT, apps_directory)


def initialize_bench(framework: dict[str, Any]) -> None:
	frappe_repository = BENCH_ROOT / "apps" / "frappe" / ".git"
	apps_registry = BENCH_ROOT / "sites" / "apps.txt"
	bench_python = BENCH_ROOT / "env" / "bin" / "python"
	if frappe_repository.is_dir() and apps_registry.is_file() and bench_python.is_file():
		return

	# A failed first run can leave an unusable partial Bench. It is safe to
	# rebuild that generated state while preserving the bind-mounted app checkout.
	for path in BENCH_ROOT.iterdir():
		if path.name == "apps":
			for app_path in path.iterdir():
				if app_path.name != "nubefact":
					shutil.rmtree(app_path)
		elif path.is_dir():
			shutil.rmtree(path)
		else:
			path.unlink()

	run(
		"bench",
		"init",
		"--ignore-exist",
		"--skip-assets",
		"--skip-redis-config-generation",
		"--python",
		sys.executable,
		"--frappe-path",
		framework["url"],
		"--frappe-branch",
		framework["branch"],
		BENCH_ROOT,
	)
	if not (BENCH_ROOT / "apps" / "frappe").is_dir():
		raise RuntimeError(f"bench init did not create a valid Bench at {BENCH_ROOT}")


def get_bench_apps() -> set[str]:
	apps_txt = BENCH_ROOT / "sites" / "apps.txt"
	if not apps_txt.exists():
		return set()
	return {line.strip() for line in apps_txt.read_text(encoding="utf-8").splitlines() if line.strip()}


def ensure_dependency_apps() -> None:
	for app in load_dependency_apps():
		repository_path = BENCH_ROOT / "apps" / app["repository_directory"]
		if app["app_name"] in get_bench_apps() and (repository_path / ".git").is_dir():
			continue
		if repository_path.exists():
			shutil.rmtree(repository_path)
		apps_txt = BENCH_ROOT / "sites" / "apps.txt"
		registered = [
			line
			for line in apps_txt.read_text(encoding="utf-8").splitlines()
			if line.strip() != app["app_name"]
		]
		apps_txt.write_text("\n".join(registered) + "\n", encoding="utf-8")
		run(
			"bench",
			"get-app",
			"--skip-assets",
			"--branch",
			app["branch"],
			app["url"],
			cwd=BENCH_ROOT,
		)


def pin_app_revisions(apps: list[dict[str, Any]]) -> None:
	for app in apps:
		repository_path = BENCH_ROOT / "apps" / app["repository_directory"]
		if not (repository_path / ".git").is_dir():
			raise RuntimeError(f"No Git repository found at {repository_path}")
		current = subprocess.run(
			["git", "rev-parse", "HEAD"],
			cwd=repository_path,
			check=True,
			capture_output=True,
			text=True,
		).stdout.strip()
		if current == app["revision"]:
			continue

		remotes = subprocess.run(
			["git", "remote"],
			cwd=repository_path,
			check=True,
			capture_output=True,
			text=True,
		).stdout.split()
		remote = "upstream" if "upstream" in remotes else "origin"
		run("git", "fetch", "--depth", "1", remote, app["revision"], cwd=repository_path)
		run("git", "checkout", "--detach", "--force", app["revision"], cwd=repository_path)
		pinned = subprocess.run(
			["git", "rev-parse", "HEAD"],
			cwd=repository_path,
			check=True,
			capture_output=True,
			text=True,
		).stdout.strip()
		if pinned != app["revision"]:
			raise RuntimeError(f"Failed to pin {app['app_name']} to {app['revision']}")


def register_nubefact() -> None:
	expected_source = BENCH_ROOT / "apps" / "nubefact"
	source = APP_SOURCE.resolve()
	if not (source / "pyproject.toml").is_file():
		raise RuntimeError(f"No Nubefact checkout found at {source}")
	if not (expected_source / "pyproject.toml").is_file():
		raise RuntimeError(f"Nubefact must also be mounted at {expected_source}")
	if not os.path.samefile(source, expected_source):
		raise RuntimeError(f"{source} and {expected_source} must expose the same checkout")

	apps_txt = BENCH_ROOT / "sites" / "apps.txt"
	apps = [line.strip() for line in apps_txt.read_text(encoding="utf-8").splitlines() if line.strip()]
	if "nubefact" not in apps:
		apps.append("nubefact")
		apps_txt.write_text("\n".join(apps) + "\n", encoding="utf-8")


def install_python_app() -> None:
	run(BENCH_ROOT / "env" / "bin" / "python", "-m", "pip", "install", "--editable", APP_SOURCE)


def configure_bench() -> None:
	settings = {
		"db_host": DB_HOST,
		"redis_cache": "redis://redis-cache:6379",
		"redis_queue": "redis://redis-queue:6379",
		"redis_socketio": "redis://redis-queue:6379",
	}
	for key, value in settings.items():
		run("bench", "set-config", "-g", key, value, cwd=BENCH_ROOT)
	run("bench", "set-config", "-gp", "db_port", DB_PORT, cwd=BENCH_ROOT)


def create_site() -> None:
	if (BENCH_ROOT / "sites" / SITE_NAME / "site_config.json").exists():
		return

	run(
		"bench",
		"new-site",
		"--db-host",
		DB_HOST,
		"--db-port",
		DB_PORT,
		"--force",
		"--db-root-username",
		"root",
		"--db-root-password",
		DB_ROOT_PASSWORD,
		"--admin-password",
		ADMIN_PASSWORD,
		"--mariadb-user-host-login-scope=%",
		SITE_NAME,
		cwd=BENCH_ROOT,
		hidden_values=(DB_ROOT_PASSWORD, ADMIN_PASSWORD),
	)


def ensure_erpnext_test_fixtures() -> None:
	result = subprocess.run(
		[
			"bench",
			"--site",
			SITE_NAME,
			"execute",
			"frappe.db.exists",
			"--args",
			'["Warehouse Type", "Transit"]',
		],
		cwd=BENCH_ROOT,
		check=True,
		capture_output=True,
		text=True,
	)
	if result.stdout.strip():
		return
	run(
		"bench",
		"--site",
		SITE_NAME,
		"execute",
		"erpnext.setup.setup_wizard.operations.install_fixtures.install",
		"--kwargs",
		'{"country": "Peru"}',
		cwd=BENCH_ROOT,
	)


def configure_site() -> None:
	installed_apps = subprocess.run(
		["bench", "--site", SITE_NAME, "list-apps", "--format", "json"],
		cwd=BENCH_ROOT,
		check=True,
		capture_output=True,
		text=True,
	).stdout
	parsed_apps = json.loads(installed_apps)
	if isinstance(parsed_apps, dict):
		installed = set(parsed_apps.get(SITE_NAME, []))
	elif isinstance(parsed_apps, list):
		installed = set(parsed_apps)
	else:
		raise RuntimeError("Unexpected output from bench list-apps --format json")
	for app in [*load_dependency_apps(), {"app_name": "nubefact"}]:
		if app["app_name"] not in installed:
			run("bench", "--site", SITE_NAME, "install-app", app["app_name"], cwd=BENCH_ROOT)

	run("bench", "--site", SITE_NAME, "set-config", "developer_mode", "1", cwd=BENCH_ROOT)
	run("bench", "--site", SITE_NAME, "set-config", "allow_tests", "true", cwd=BENCH_ROOT)
	run("bench", "--site", SITE_NAME, "set-config", "host_name", f"http://{SITE_NAME}:8000", cwd=BENCH_ROOT)
	run("bench", "--site", SITE_NAME, "migrate", cwd=BENCH_ROOT)
	ensure_erpnext_test_fixtures()
	run("bench", "use", SITE_NAME, cwd=BENCH_ROOT)


def main() -> None:
	framework = load_framework_app()
	prepare_bench_mount()
	initialize_bench(framework)
	pin_app_revisions([framework])
	register_nubefact()
	install_python_app()
	ensure_dependency_apps()
	pin_app_revisions(load_apps())
	run("bench", "setup", "requirements", "--dev", cwd=BENCH_ROOT)
	configure_bench()
	create_site()
	configure_site()
	run("bench", "build", "--app", "nubefact", cwd=BENCH_ROOT)
	print(
		f"\nDevelopment Bench ready at {BENCH_ROOT}. Tests:\n  bench --site {SITE_NAME} run-tests --app nubefact",
		flush=True,
	)


if __name__ == "__main__":
	main()
