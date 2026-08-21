from .base import PlatformAdapter
class SnowflakeAdapter(PlatformAdapter):
    name="snowflake"
    def plan(self, canonical):
        return {"platform":self.name,"services":["Snowpipe","Streams","Tasks","Dynamic Tables","Cortex","Governance"],"status":"generated"}
