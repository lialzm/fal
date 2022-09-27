from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any

from fal.packages.dependency_analysis import get_default_pip_dependencies
from fal.packages.environments.base import (
    BASE_CACHE_DIR,
    BaseEnvironment,
    DualPythonIPC,
    get_executable_path,
    log_env,
    python_path_for,
    rmdir_on_fail,
)
from fal.utils import cache_static

_BASE_VENV_DIR = BASE_CACHE_DIR / "venvs"
_BASE_VENV_DIR.mkdir(exist_ok=True)


@dataclass
class VirtualPythonEnvironment(BaseEnvironment[Path], make_thread_safe=True):
    requirements: List[str]

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> VirtualPythonEnvironment:
        requirements = config.get("requirements", [])
        return cls(requirements)

    @property
    def key(self) -> str:
        return hashlib.sha256(" ".join(self.requirements).encode()).hexdigest()

    def _verify_dependencies(self, primary_path: Path, secondary_path: Path) -> None:
        # Ensure that there are no dependency mismatches between the
        # primary environment and the secondary environment.
        python_path = python_path_for(secondary_path, primary_path)
        original_pip = get_executable_path(primary_path, "pip")
        subprocess.check_call([original_pip, "check"], env={"PYTHONPATH": python_path})

    def _get_or_create(self) -> Path:
        from virtualenv import cli_run

        path = _BASE_VENV_DIR / self.key
        if path.exists():
            return path

        with rmdir_on_fail(path):
            log_env(self, "Creating virtual environment at {}", path, kind="info")
            cli_run([str(path)])
            log_env(
                self,
                "Installing requirements: {}",
                ", ".join(self.requirements),
                kind="info",
            )
            if self.requirements:
                pip_path = get_executable_path(path, "pip")
                subprocess.check_call([pip_path, "install"] + self.requirements)

            primary_env = get_primary_virtual_env()
            if self is not primary_env:
                self._verify_dependencies(primary_env._get_or_create(), path)

        return path

    def open_connection(self, conn_info: Path) -> DualPythonIPC:
        primary_venv = get_primary_virtual_env()
        primary_venv_path = primary_venv.get_or_create()
        secondary_venv_path = conn_info
        return DualPythonIPC(self, primary_venv_path, secondary_venv_path)


@cache_static
def get_primary_virtual_env() -> VirtualPythonEnvironment:
    return VirtualPythonEnvironment(get_default_pip_dependencies())