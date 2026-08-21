from .base import PlatformAdapter
class AWSAdapter(PlatformAdapter):
    name="aws"
    def plan(self, canonical):
        return {"platform":self.name,"services":["S3","Glue","Lake Formation","Redshift","Athena","Step Functions"],"status":"generated"}
