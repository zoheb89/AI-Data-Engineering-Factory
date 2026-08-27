
from __future__ import annotations
from pathlib import Path
import os, io

class ObjectStorage:
    """Provider-neutral artifact/document storage interface.

    LOCAL is the default for development. S3/Azure/GCS implementations can be
    enabled without changing project/artifact business logic.
    """
    def __init__(self):
        self.backend=os.getenv("OBJECT_STORAGE_BACKEND","local").lower()
        self.root=Path(os.getenv("OBJECT_STORAGE_LOCAL_ROOT","data/objects"))
        self.root.mkdir(parents=True,exist_ok=True)

    def put_bytes(self,key,data,content_type="application/octet-stream"):
        safe=Path(key)
        path=self.root/safe
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data)
        return {"backend":"local","key":str(safe),"content_type":content_type,"size":len(data)}

    def get_bytes(self,key):
        return (self.root/Path(key)).read_bytes()

    def exists(self,key): return (self.root/Path(key)).exists()
