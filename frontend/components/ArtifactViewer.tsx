'use client';
/**
 * Renders the artifacts a stage produced. The backend has always persisted
 * these via /artifacts and /artifacts/{kind}; nothing in the UI read them,
 * so generated deliverables were invisible. This is that missing surface.
 */
import {useEffect, useMemo, useState} from 'react';
import {FileJson, Download, RefreshCw, Copy, Check, FileText, ChevronRight} from 'lucide-react';
import {getArtifacts, getArtifact, type ArtifactSummary} from '../lib/api';

function download(name: string, content: string) {
  const blob = new Blob([content], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function prettify(content: any): string {
  if (content == null) return '';
  if (typeof content === 'string') {
    try { return JSON.stringify(JSON.parse(content), null, 2); } catch { return content; }
  }
  try { return JSON.stringify(content, null, 2); } catch { return String(content); }
}

/** Human labels for backend artifact kinds. */
const KIND_LABELS: Record<string, string> = {
  intake_pack: 'Intake Pack',
  discovery: 'Discovery Evidence',
  environment_assessment: 'Environment Assessment',
  assessment: 'Current-State Assessment',
  blueprint: 'Solution Blueprint',
  architecture: 'Architecture',
  metadata: 'Engineering Metadata',
  engineering: 'Engineering Components',
  qa: 'Quality Evidence',
  full_qa: 'Full QA Evidence',
  bi: 'BI & Analytics Products',
  application: 'Application Assets',
  validation: 'Validation Results',
  platform: 'Platform Configuration',
};
export function kindLabel(kind: string) {
  return KIND_LABELS[kind] || kind.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export function ArtifactViewer({
  engagementId,
  filterKinds,
  title = 'Generated artifacts',
  emptyHint = 'Run this stage to generate governed artifacts.',
}: {
  engagementId: string | null;
  filterKinds?: string[];
  title?: string;
  emptyHint?: string;
}) {
  const [items, setItems] = useState<ArtifactSummary[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const [copied, setCopied] = useState(false);

  const load = async () => {
    if (!engagementId) return;
    setLoading(true);
    setErr('');
    try {
      const r = await getArtifacts(engagementId);
      const all = r.items || [];
      const shown = filterKinds?.length ? all.filter(a => filterKinds.includes(a.kind)) : all;
      setItems(shown);
      if (shown.length && !shown.some(a => a.kind === active)) setActive(shown[0].kind);
    } catch (e: any) {
      setErr(e?.message || 'Unable to load artifacts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [engagementId, filterKinds?.join(',')]);

  useEffect(() => {
    if (!engagementId || !active) { setDetail(null); return; }
    let cancelled = false;
    getArtifact(engagementId, active)
      .then(r => { if (!cancelled) setDetail(r.artifact); })
      .catch(() => { if (!cancelled) setDetail(null); });
    return () => { cancelled = true; };
  }, [engagementId, active]);

  const text = useMemo(() => prettify(detail?.content), [detail]);

  if (!engagementId) return null;

  return (
    <section className="panel artifactPanel">
      <div className="panelHead">
        <h3><FileJson size={18} /> {title}</h3>
        <button className="secondary sm" onClick={load} disabled={loading}>
          <RefreshCw size={15} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>

      {err && <div className="notice error">{err}</div>}

      {items.length === 0 ? (
        <div className="empty"><FileText size={18} /> {loading ? 'Loading artifacts…' : emptyHint}</div>
      ) : (
        <div className="artifactLayout">
          <ul className="artifactList">
            {items.map(a => (
              <li key={a.id || a.kind}>
                <button
                  className={a.kind === active ? 'artifactItem active' : 'artifactItem'}
                  onClick={() => setActive(a.kind)}
                >
                  <span>{kindLabel(a.kind)}</span>
                  <ChevronRight size={14} />
                </button>
              </li>
            ))}
          </ul>

          <div className="artifactBody">
            {detail ? (
              <>
                <div className="artifactBar">
                  <code>{detail.kind}</code>
                  <div className="artifactActions">
                    <button
                      className="secondary sm"
                      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
                    >
                      {copied ? <Check size={15} /> : <Copy size={15} />} {copied ? 'Copied' : 'Copy'}
                    </button>
                    <button className="secondary sm" onClick={() => download(`${detail.kind}.json`, text)}>
                      <Download size={15} /> Download
                    </button>
                  </div>
                </div>
                <pre className="artifactCode">{text}</pre>
              </>
            ) : (
              <div className="empty">Select an artifact to inspect its evidence.</div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
