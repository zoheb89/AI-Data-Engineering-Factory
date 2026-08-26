export const API_BASE=process.env.NEXT_PUBLIC_API_BASE_URL||'http://localhost:8000';

export type IntakeResult={
  engagement_id:string; name:string; document_type:string|Record<string,number>;
  status:string; extracted_summary?:string; analysis?:any; bundle_size?:number;
};

async function request<T>(path:string, init?:RequestInit):Promise<T>{
  const r=await fetch(`${API_BASE}${path}`,{...init,headers:{'Content-Type':'application/json',...(init?.headers||{})}});
  if(!r.ok){const msg=await r.text();throw new Error(msg||`API ${r.status}`)}
  return r.json();
}

export async function listProjects(){return request<any>('/api/projects')}
export async function getProject(id:string){return request<any>(`/api/projects/${id}`)}

export async function createIntake(p:{name:string;text?:string;file?:File;projectId?:string}):Promise<IntakeResult>{
  const f=new FormData(); f.append('name',p.name||'New Customer Project');
  if(p.text)f.append('text',p.text); if(p.projectId)f.append('project_id',p.projectId); if(p.file)f.append('file',p.file);
  const r=await fetch(`${API_BASE}/api/intake`,{method:'POST',body:f});
  if(!r.ok){const msg=await r.text();throw new Error(msg||`API ${r.status}`)}
  const result=await r.json();
  if(typeof window!=='undefined') localStorage.setItem('eliteintelia.projectId',result.engagement_id);
  return result;
}

export async function runStage(projectId:string,stage:string,prompt='',context:any={}){
  return request<any>(`/api/projects/${projectId}/stage/${stage}`,{method:'POST',body:JSON.stringify({prompt,context})});
}

export function currentProjectId(){return typeof window==='undefined'?'':localStorage.getItem('eliteintelia.projectId')||''}
