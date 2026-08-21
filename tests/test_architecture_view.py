from c_invent.services.architecture_view import platform_fit, architecture_model

def test_platform_fit_is_normalized_and_ranked():
    d = {
        "summary": "Modernize hospital data platform",
        "domain": "healthcare",
        "objectives": ["data engineering", "analytics", "future AI/BI"],
        "requirements": ["medallion architecture", "governance", "SQL Server", "Azure"],
    }
    rows = platform_fit(d, {}, {})
    assert rows
    assert rows[0]["fit_score"] > 0
    assert abs(sum(r["relative_share"] for r in rows) - 100) < 1.0

def test_architecture_model_is_platform_neutral():
    model = architecture_model({"systems": ["on_prem_sql_server_hms_db"]}, {}, "Snowflake")
    assert model["source"]["title"]
    assert model["platform"]["title"] == "Snowflake"
    assert model["bronze"]["title"] == "Bronze"
