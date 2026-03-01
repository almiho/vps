import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"


def _load_config() -> dict:
	"""Load TARGET_HOST_ALIAS and TARGET_PUBLIC_IP from tests/config.env."""
	config_path = TESTS_DIR / "config.env"
	values: dict[str, str] = {}
	for line in config_path.read_text().splitlines():
		line = line.strip()
		if not line or line.startswith("#"):
			continue
		if "=" not in line:
			continue
		key, val = line.split("=", 1)
		values[key.strip()] = val.strip().strip('"')
	return values


def _ssh_base_cmd(target_host: str) -> list[str]:
	"""Base SSH command matching the shell helpers (BatchMode, timeouts)."""
	return [
		"ssh",
		"-o",
		"BatchMode=yes",
		"-o",
		"ConnectTimeout=5",
		"-o",
		"ConnectionAttempts=1",
		target_host,
	]


def test_ssh_reachable_basic_connectivity():
	"""SMOKE: SSH must be reachable and able to run a trivial command."""
	config = _load_config()
	target = config["TARGET_HOST_ALIAS"]
	cmd = _ssh_base_cmd(target) + ["echo ok >/dev/null"]
	result = subprocess.run(
		cmd,
		cwd=PROJECT_ROOT,
		text=True,
		capture_output=True,
	)
	assert (
		result.returncode == 0
	), f"SSH reachability failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


def test_ssh_key_based_authentication_works():
	"""AUDIT: key-based SSH authentication should succeed when passwords are disabled."""
	config = _load_config()
	target = config["TARGET_HOST_ALIAS"]
	cmd = [
		"ssh",
		"-o",
		"BatchMode=yes",
		"-o",
		"ConnectTimeout=5",
		"-o",
		"ConnectionAttempts=1",
		"-o",
		"PasswordAuthentication=no",
		target,
		"echo ok >/dev/null",
	]
	result = subprocess.run(
		cmd,
		cwd=PROJECT_ROOT,
		text=True,
		capture_output=True,
	)
	assert (
		result.returncode == 0
	), f"Key-based SSH auth failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


def test_ssh_password_authentication_appears_disabled():
	"""AUDIT: password-only SSH login should be rejected from the outside.

	We mimic tests/audit.sh by attempting a password-only auth with zero
	password prompts and then checking for a publickey-style denial.
	"""
	config = _load_config()
	target = config["TARGET_HOST_ALIAS"]
	cmd = [
		"ssh",
		"-o",
		"BatchMode=yes",
		"-o",
		"ConnectTimeout=5",
		"-o",
		"ConnectionAttempts=1",
		"-o",
		"PreferredAuthentications=password",
		"-o",
		"PubkeyAuthentication=no",
		"-o",
		"NumberOfPasswordPrompts=0",
		target,
		"true",
	]
	result = subprocess.run(
		cmd,
		cwd=PROJECT_ROOT,
		text=True,
		capture_output=True,
	)
	output = result.stdout + result.stderr
	assert "Permission denied (publickey" in output, (
		"SSH password auth may still be enabled or response is unexpected.\n"
		f"Exit code: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
	)
