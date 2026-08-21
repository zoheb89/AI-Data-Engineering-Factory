from .base import PlatformAdapter
class DatabricksAdapter(PlatformAdapter):
    name="databricks"
    def plan(self, canonical):
        return {"platform":self.name,"services":["Delta Lake","Unity Catalog","Lakeflow","Jobs","SQL","AI/BI","Lakebase","Databricks Apps"],"status":"generated"}
