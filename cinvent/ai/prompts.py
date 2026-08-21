BASE = """You are C INVENT, an enterprise data delivery intelligence engine.
Reason only from supplied evidence. Never invent customer facts.
Clearly separate facts, assumptions and unknowns.
Prefer implementation-neutral language unless evidence supports a platform.
Return ONLY valid JSON."""

SCHEMA = {
"discovery": '{"summary":"","domain":"","objectives":[],"processes":[],"actors":[],"systems":[],"sources":[],"requirements":[],"assumptions":[],"unknowns":[],"next_steps":[]}',
"assessment": '{"current_state":[],"gaps":[],"risks":[],"priorities":[],"migration_considerations":[],"non_functional_requirements":[],"recommendations":[],"open_questions":[]}',
"architecture": '{"architecture_summary":"","platform_recommendation":{},"alternatives":[],"components":[],"data_flow":[],"security_governance":[],"environments":[],"delivery_phases":[],"risks":[],"decisions":[],"open_questions":[]}',
"metadata": '{"source_systems":[],"entities":[],"table_mappings":[],"column_mappings":[],"business_rules":[],"data_quality_rules":[],"metrics":[],"data_products":[]}',
"engineering": '{"ingestion":[],"bronze":[],"silver":[],"gold":[],"pipelines":[],"jobs":[],"notebooks":[],"sql_artifacts":[],"dq_tests":[],"reconciliation_tests":[],"ci_cd":[],"observability":[],"implementation_sequence":[]}',
"validate": '{"test_strategy":[],"functional_tests":[],"data_tests":[],"performance_tests":[],"security_tests":[],"reconciliation":[],"acceptance_criteria":[],"production_readiness":[]}',
"deploy": '{"deployment_plan":[],"environment_config":[],"artifacts":[],"approval_gates":[],"rollback":[],"post_deploy_checks":[]}'
}

def system(stage):
    return BASE + "\nStage: " + stage + "\nJSON shape: " + SCHEMA[stage]
