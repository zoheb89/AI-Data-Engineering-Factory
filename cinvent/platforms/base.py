from dataclasses import dataclass
@dataclass
class PlatformResult:
    ok: bool
    message: str
    details: dict
class PlatformAdapter:
    name="generic"
    def plan(self, canonical): return {"platform":self.name,"status":"planned","canonical":canonical}
    def apply(self, plan, allow_mutations=False):
        if not allow_mutations: return PlatformResult(False,"Mutation blocked by safety gate",{})
        return PlatformResult(False,"Mutation adapter not implemented",{})
