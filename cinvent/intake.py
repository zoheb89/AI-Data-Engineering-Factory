from pathlib import Path
from cinvent.config import settings
from cinvent.db import add_evidence
import re, io

def safe(name): return re.sub(r"[^A-Za-z0-9._-]+","_",name)

def extract(name,data):
    ext=Path(name).suffix.lower()
    try:
        if ext in [".txt",".csv",".json",".yaml",".yml"]: return data.decode("utf-8","ignore")
        if ext==".pdf":
            from pypdf import PdfReader
            return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        if ext==".docx":
            from docx import Document
            return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
        if ext==".xlsx":
            import pandas as pd
            x=pd.ExcelFile(io.BytesIO(data)); out=[]
            for s in x.sheet_names:
                df=pd.read_excel(x,sheet_name=s,dtype=str).fillna("")
                out.append(f"## SHEET {s}\n{df.to_csv(index=False)}")
            return "\n".join(out)
    except Exception as e:
        return f"[Extraction error: {e}]"
    return "[No text extraction available]"

def save_upload(pid, uploaded):
    data=uploaded.getvalue()
    folder=Path(settings.ARTIFACT_STORE_PATH)/"evidence"/pid
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/safe(uploaded.name)
    path.write_bytes(data)
    add_evidence(pid,uploaded.name,str(path),extract(uploaded.name,data))
    return path
