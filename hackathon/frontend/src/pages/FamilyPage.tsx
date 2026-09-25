import { useEffect, useState } from "react";
import { CalendarDays, FileText, FolderTree, GitBranch, Landmark, Layers3 } from "lucide-react";
import { Link, useLocation, useParams } from "react-router-dom";

import {
  DocumentNotFoundError,
  fetchDocument,
  type DocumentDetail,
  type VersionSummary,
} from "../api/documents";
import type { MatchedChunk } from "../api/search";
import { DemoBanner } from "../components/DemoBanner";
import { RelationsPanel } from "../components/RelationsPanel";

/**
 * Pagina de familia/documento (TB1 Ticket 4, issue #20).
 *
 * Substitui o placeholder registrado em "/documents/:familyId" pelo
 * Ticket 3 (issue #19). Consome GET /v1/documents/{familyId}, sem
 * "version" na primeira carga (o backend ja devolve a versao mais
 * recente por padrao - AC1) e refaz a busca com "?version=" quando o
 * usuario clica numa entrada da linha do tempo.
 *
 * Os ``matched_chunks`` do card de busca que levou ate aqui chegam via
 * state do react-router (nunca a URL - ver SearchPage.tsx, o Link usa
 * `state={{ matchedChunks: result.matched_chunks }}`). Acessar esta
 * pagina direto (refresh, link colado) e um caminho valido: o state
 * fica vazio e a pagina funciona igual, so sem nenhum destaque no
 * texto - nao e erro.
 *
 * Ticket 5 (issue #21) adiciona o painel "Relações" (RelationsPanel,
 * ../components/RelationsPanel.tsx) ao final da pagina, centrado em
 * `detail.family_id` - sem remover nada do que ja existia.
 */

type LocationState = {
  matchedChunks?: MatchedChunk[];
};

type FamilyState =
  | { kind: "loading" }
  | { kind: "result"; detail: DocumentDetail }
  | { kind: "not-found" }
  | { kind: "error" };

export function FamilyPage() {
  const { familyId } = useParams<{ familyId: string }>();
  const location = useLocation();
  const matchedChunks = (location.state as LocationState | null)?.matchedChunks ?? [];

  const [state, setState] = useState<FamilyState>({ kind: "loading" });

  function load(version?: string) {
    if (!familyId) {
      return;
    }
    setState({ kind: "loading" });
    fetchDocument(familyId, version)
      .then((detail) => setState({ kind: "result", detail }))
      .catch((error: unknown) => {
        if (error instanceof DocumentNotFoundError) {
          setState({ kind: "not-found" });
        } else {
          setState({ kind: "error" });
        }
      });
  }

  useEffect(() => {
    load();
    // so recarrega quando o family_id da rota muda - "load" e recriada a
    // cada render mas so precisa rodar de novo com um family_id diferente.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [familyId]);

  return (
    <div className="page detail-page">
      <DemoBanner />

      <section aria-label="página de família">
        {state.kind === "loading" && <div className="loading-state"><span className="loading-spinner" aria-hidden="true" /> Carregando...</div>}
        {state.kind === "not-found" && <div className="empty-state"><h2>Família não encontrada.</h2><Link to="/">Voltar à consulta</Link></div>}
        {state.kind === "error" && <div className="empty-state error-state"><h2>Não foi possível carregar o documento.</h2><p>Tente novamente em alguns instantes.</p></div>}
        {state.kind === "result" && (
          <FamilyContent
            detail={state.detail}
            matchedChunks={matchedChunks}
            onSelectVersion={(documentVersion) => load(documentVersion)}
          />
        )}
      </section>
    </div>
  );
}

type Segment =
  | { highlighted: false; text: string }
  | { highlighted: true; text: string; chunk: MatchedChunk };

function buildHighlightedSegments(text: string, chunks: MatchedChunk[]): Segment[] {
  const matches: { start: number; end: number; chunk: MatchedChunk }[] = [];
  for (const chunk of chunks) {
    const start = text.indexOf(chunk.excerpt);
    if (start === -1) {
      continue;
    }
    matches.push({ start, end: start + chunk.excerpt.length, chunk });
  }
  matches.sort((a, b) => a.start - b.start);

  const segments: Segment[] = [];
  let cursor = 0;
  for (const match of matches) {
    if (match.start < cursor) {
      // trechos sobrepostos - mantem so o primeiro, na ordem em que aparecem no texto
      continue;
    }
    if (match.start > cursor) {
      segments.push({ highlighted: false, text: text.slice(cursor, match.start) });
    }
    segments.push({ highlighted: true, text: text.slice(match.start, match.end), chunk: match.chunk });
    cursor = match.end;
  }
  if (cursor < text.length) {
    segments.push({ highlighted: false, text: text.slice(cursor) });
  }
  return segments;
}

function FamilyContent({
  detail,
  matchedChunks,
  onSelectVersion,
}: {
  detail: DocumentDetail;
  matchedChunks: MatchedChunk[];
  onSelectVersion: (documentVersion: string) => void;
}) {
  const selected = detail.selected_version;
  const chunksInSelectedVersion = matchedChunks.filter(
    (chunk) => chunk.document_version === selected.document_version,
  );
  const versionsWithChunkElsewhere = new Set(
    matchedChunks
      .filter((chunk) => chunk.document_version !== selected.document_version)
      .map((chunk) => chunk.document_version),
  );

  const dateSourceLabel =
    selected.version_date_source === "publication" ? "publicação" : "coleta";

  const segments = buildHighlightedSegments(selected.text, chunksInSelectedVersion);

  return (
    <div className="detail-layout">
      <div className="detail-primary">
        <header className="document-header">
          <Link className="back-link" to="/explorar">Voltar à pesquisa</Link>
          <p className="eyebrow"><FileText size={15} /> Família documental</p>
          <h1>
            {formatDocumentType(detail.document_type)}
            <span className="sr-only">{detail.document_type}</span>
          </h1>
          <div className="document-facts">
            <span><FolderTree size={16} /> Identificador: {detail.document_id}</span>
            {detail.processo_numero && (
              <span>
                <Landmark size={16} /> Processo: {detail.processo_numero}
                <Link className="fact-action" to={`/processos/${encodeURIComponent(detail.processo_numero)}`}>Abrir processo</Link>
              </span>
            )}
            <span><CalendarDays size={16} /> Data ({dateSourceLabel}): {selected.version_date}</span>
          </div>
        </header>

        <nav className="version-timeline" aria-label="linha do tempo de versões">
          <div className="section-heading"><div><p className="eyebrow"><Layers3 size={15} /> Histórico documental</p><h2>Versões registradas</h2></div><span>{detail.versions.length} versão{detail.versions.length > 1 ? "ões" : ""}</span></div>
          <ul>
          {detail.versions.map((version: VersionSummary) => {
            const isSelected = version.document_version === selected.document_version;
            const hasRelevantChunkElsewhere = versionsWithChunkElsewhere.has(
              version.document_version,
            );
            return (
              <li key={version.document_version}>
                <button
                  type="button"
                  onClick={() => onSelectVersion(version.document_version)}
                  aria-current={isSelected ? "true" : undefined}
                >
                  <span>{version.version_date}</span><small>{isSelected ? "Versão selecionada" : "Ver versão"}</small>
                </button>
                {hasRelevantChunkElsewhere && <span className="relevant-flag">Trecho relevante aqui</span>}
              </li>
            );
          })}
          </ul>
        </nav>

        <article className="document-text" aria-label="texto da versão selecionada">
          <div className="section-heading"><div><p className="eyebrow"><FileText size={15} /> Conteúdo</p><h2>{selected.document_version}</h2></div><span>Fonte: {dateSourceLabel}</span></div>
          <div className="document-body">
            {segments.map((segment, index) =>
              segment.highlighted ? (
                <span key={index}>
                  <mark>{segment.text}</mark>
                  <em> Trecho da busca — {segment.chunk.is_latest ? "versão mais recente" : "não é a versão mais recente"}</em>
                </span>
              ) : (
                <span key={index}>{segment.text}</span>
              ),
            )}
          </div>
        </article>
      </div>

      <aside className="detail-sidebar">
        <div className="sidebar-title"><GitBranch size={17} /><span>Contexto conectado</span></div>
        <RelationsPanel nodeId={detail.family_id} />
      </aside>
    </div>
  );
}

function formatDocumentType(value: string) {
  const readable = value.replaceAll("_", " ");
  return `${readable.slice(0, 1).toUpperCase()}${readable.slice(1)}`;
}

export default FamilyPage;
