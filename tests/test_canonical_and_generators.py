from pathlib import Path
from cinvent.canonical import CanonicalDeliveryModel, Mapping, DataQualityRule, Pipeline
from cinvent.generators import generate_pack

def test_canonical_generates_artifacts(tmp_path):
    model=CanonicalDeliveryModel(
        customer="Demo",
        project="Hospital HMS",
        intent="Modernize data platform",
        mappings=[Mapping(source_system="SQLServer",source_table="patient",
                          source_column="patient_id",target_layer="silver",
                          target_table="patient",target_column="patient_id")],
        quality_rules=[DataQualityRule(id="DQ-001",name="PK not null",
                         rule_type="not_null",target="patient.patient_id",
                         expression="patient_id IS NOT NULL")],
        pipelines=[Pipeline(name="patient_ingestion",source="SQLServer.patient",
                            target="bronze.patient")]
    )
    files=generate_pack(model,str(tmp_path))
    names={Path(x["path"]).relative_to(tmp_path).as_posix() for x in files}
    assert "hospital_hms/canonical/canonical_delivery_model.json" in names
    assert "hospital_hms/metadata/source_target_mapping.csv" in names
    assert "hospital_hms/platforms/databricks/lakeflow.pipeline.yml" in names
    assert len(files) >= 10
