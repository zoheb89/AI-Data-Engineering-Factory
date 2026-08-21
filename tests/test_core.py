def test_platform_adapters():
    from cinvent.platforms.databricks import DatabricksAdapter
    from cinvent.platforms.fabric import FabricAdapter
    from cinvent.platforms.snowflake import SnowflakeAdapter
    from cinvent.platforms.aws import AWSAdapter
    assert DatabricksAdapter().name=="databricks"
    assert FabricAdapter().name=="microsoft_fabric"
    assert SnowflakeAdapter().name=="snowflake"
    assert AWSAdapter().name=="aws"
