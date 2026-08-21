"""C INVENT Canonical Delivery Model.

The canonical model is platform- and domain-neutral. Platform adapters consume it
to generate implementation artifacts.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
import uuid

class SourceColumn(BaseModel):
    name: str
    data_type: str = "string"
    nullable: bool = True
    description: str = ""

class SourceTable(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    schema_name: str = "dbo"
    source_system: str = ""
    primary_key: List[str] = Field(default_factory=list)
    columns: List[SourceColumn] = Field(default_factory=list)
    incremental_column: Optional[str] = None
    estimated_rows: Optional[int] = None

class Entity(BaseModel):
    name: str
    description: str = ""
    source_tables: List[str] = Field(default_factory=list)
    business_keys: List[str] = Field(default_factory=list)

class Mapping(BaseModel):
    source_system: str
    source_table: str
    source_column: str
    target_layer: str
    target_table: str
    target_column: str
    transformation: str = "pass-through"
    data_type: str = "string"
    nullable: bool = True

class DataQualityRule(BaseModel):
    id: str
    name: str
    rule_type: str
    target: str
    expression: str
    severity: str = "error"
    action: str = "quarantine"

class Metric(BaseModel):
    name: str
    description: str = ""
    expression: str = ""
    grain: str = ""
    owner: str = ""

class Pipeline(BaseModel):
    name: str
    source: str
    target: str
    mode: str = "incremental"
    schedule: str = "0 0 * * *"
    dependencies: List[str] = Field(default_factory=list)

class DataProduct(BaseModel):
    name: str
    description: str = ""
    domain: str = ""
    gold_tables: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    consumers: List[str] = Field(default_factory=list)

class PlatformDecision(BaseModel):
    cloud: str = "undecided"
    platform: str = "undecided"
    rationale: str = ""
    alternatives: List[str] = Field(default_factory=list)

class CanonicalDeliveryModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: str = "1.0"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    customer: str
    project: str
    domain: str = ""
    intent: str
    requirements: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    processes: List[str] = Field(default_factory=list)
    systems: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    platform_decision: PlatformDecision = Field(default_factory=PlatformDecision)
    source_tables: List[SourceTable] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)
    mappings: List[Mapping] = Field(default_factory=list)
    quality_rules: List[DataQualityRule] = Field(default_factory=list)
    pipelines: List[Pipeline] = Field(default_factory=list)
    metrics: List[Metric] = Field(default_factory=list)
    data_products: List[DataProduct] = Field(default_factory=list)
    bronze_strategy: Dict[str, Any] = Field(default_factory=dict)
    silver_strategy: Dict[str, Any] = Field(default_factory=dict)
    gold_strategy: Dict[str, Any] = Field(default_factory=dict)
    security: Dict[str, Any] = Field(default_factory=dict)
    environments: List[str] = Field(default_factory=lambda: ["dev", "test", "prod"])
    decisions: List[Dict[str, Any]] = Field(default_factory=list)

def model_from_artifacts(project: Dict[str, Any], artifacts: Dict[str, Any]) -> CanonicalDeliveryModel:
    d = artifacts.get("discovery", {}) or {}
    a = artifacts.get("assessment", {}) or {}
    ar = artifacts.get("architecture", {}) or {}
    m = artifacts.get("metadata", {}) or {}
    e = artifacts.get("engineering", {}) or {}

    platform = ar.get("platform_recommendation", {}) or {}
    pd = PlatformDecision(
        cloud=platform.get("cloud", "undecided"),
        platform=platform.get("platform", project.get("platform") or "undecided"),
        rationale=platform.get("rationale", ar.get("architecture_summary", "")),
        alternatives=[str(x) for x in (ar.get("alternatives", []) or [])],
    )

    mappings = []
    for x in m.get("table_mappings", []) or []:
        if isinstance(x, dict):
            mappings.append(Mapping(
                source_system=str(x.get("source_system", "")),
                source_table=str(x.get("source_table", x.get("source", ""))),
                source_column=str(x.get("source_column", "")),
                target_layer=str(x.get("target_layer", "silver")),
                target_table=str(x.get("target_table", x.get("target", ""))),
                target_column=str(x.get("target_column", x.get("source_column", ""))),
                transformation=str(x.get("transformation", "pass-through")),
                data_type=str(x.get("data_type", "string")),
                nullable=bool(x.get("nullable", True)),
            ))

    rules=[]
    for i, x in enumerate(m.get("data_quality_rules", []) or [], 1):
        if isinstance(x, dict):
            rules.append(DataQualityRule(
                id=str(x.get("id", f"DQ-{i:03d}")),
                name=str(x.get("name", f"Rule {i}")),
                rule_type=str(x.get("rule_type", x.get("type", "not_null"))),
                target=str(x.get("target", "")),
                expression=str(x.get("expression", x.get("rule", ""))),
                severity=str(x.get("severity", "error")),
                action=str(x.get("action", "quarantine")),
            ))

    pipelines=[]
    for i, x in enumerate(e.get("pipelines", []) or [], 1):
        if isinstance(x, dict):
            pipelines.append(Pipeline(
                name=str(x.get("name", f"pipeline_{i}")),
                source=str(x.get("source", "")),
                target=str(x.get("target", "")),
                mode=str(x.get("mode", "incremental")),
                schedule=str(x.get("schedule", "0 0 * * *")),
                dependencies=[str(y) for y in (x.get("dependencies", []) or [])],
            ))

    return CanonicalDeliveryModel(
        customer=project["customer"],
        project=project["name"],
        domain=project.get("domain") or d.get("domain", ""),
        intent=project["intent"],
        requirements=[str(x) for x in (d.get("requirements", []) or [])],
        assumptions=[str(x) for x in (d.get("assumptions", []) or [])],
        unknowns=[str(x) for x in (d.get("unknowns", []) or [])],
        processes=[str(x) for x in (d.get("processes", []) or [])],
        systems=[str(x) for x in (d.get("systems", []) or [])],
        sources=[str(x) for x in (d.get("sources", []) or [])],
        platform_decision=pd,
        source_tables=[SourceTable.model_validate(x) for x in (m.get("source_tables", []) or []) if isinstance(x, dict)],
        entities=[Entity.model_validate(x) for x in (m.get("entities", []) or []) if isinstance(x, dict)],
        mappings=mappings,
        quality_rules=rules,
        pipelines=pipelines,
        metrics=[Metric.model_validate(x) for x in (m.get("metrics", []) or []) if isinstance(x, dict)],
        data_products=[DataProduct.model_validate(x) for x in (m.get("data_products", []) or []) if isinstance(x, dict)],
        bronze_strategy={"pattern": "raw/append-or-cdc", "partitioning": "source ingestion date"},
        silver_strategy={"pattern": "conformed/validated", "deduplication": "business key + latest change"},
        gold_strategy={"pattern": "business-ready dimensional/semantic"},
        security=ar.get("security_governance", {}) if isinstance(ar.get("security_governance", {}), dict) else {"controls": ar.get("security_governance", [])},
        environments=["dev","test","prod"],
        decisions=ar.get("decisions", []) or [],
    )
