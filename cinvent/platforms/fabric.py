from .base import PlatformAdapter
class FabricAdapter(PlatformAdapter):
    name="microsoft_fabric"
    def plan(self, canonical):
        return {"platform":self.name,"services":["OneLake","Lakehouse","Data Factory","Warehouse","Power BI"],"status":"generated"}
