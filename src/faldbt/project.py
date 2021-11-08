from dataclasses import dataclass
from os import name
from typing import Dict, List, Optional, List, Any, TypeVar
from pydantic import BaseModel
from pathlib import Path
from dbt.contracts.graph.manifest import Manifest


class FalGeneralException(Exception):
    pass


@dataclass
class DbtManifest:
    nativeManifest: Manifest


class DbtModel(BaseModel):
    name: str
    meta: Optional[Dict[str, Any]] = {}
    description: str
    columns: Any

    def model_key(self, project_name):
        return "model." + project_name + "." + self.name


class DbtRunResult(BaseModel):
    status: str
    timing: List[Any]
    thread_id: str
    execution_time: int
    adapter_response: Dict[str, str]
    message: str
    failures: Any
    unique_id: str


class DbtRunResultFile(BaseModel):
    metadata: Any
    results: List[DbtRunResult]


T = TypeVar("T", bound="DbtProject")


@dataclass
class DbtProject:
    name: str
    model_config_paths: List[str]
    models: List[DbtModel]
    manifest: DbtManifest
    keyword: str
    scripts: List[Path]
    results: DbtRunResultFile

    def state_has_changed(self, other: DbtManifest) -> bool:
        return self.manifest != other

    def find_model_location(self, model: DbtModel) -> List[str]:
        model_node = self.manifest.nodes[model.model_key(self.name)]
        return model_node.relation_name.replace("`", "")
