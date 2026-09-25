import { Eye, FileText, FolderKanban, RefreshCw, Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchProcessos, type ProcessoSummary } from "../api/processos";
import { PageHero } from "../components/layout/PageHero";

type ProcessState =
  | { kind: "loading" }
  | { kind: "ready"; processes: ProcessoSummary[] }
  | { kind: "error" };

export function MyProcessesPage() {
  const navigate = useNavigate();
  const [state, setState] = useState<ProcessState>({ kind: "loading" });
  const [query, setQuery] = useState("");

  const load = useCallback(() => {
    setState({ kind: "loading" });
    fetchProcessos()
      .then((processes) => setState({ kind: "ready", processes }))
      .catch(() => setState({ kind: "error" }));
  }, []);

  useEffect(load, [load]);

  const processes = useMemo(() => {
    if (state.kind !== "ready") return [];
    const normalizedQuery = query.trim().toLocaleLowerCase("pt-BR");
    if (!normalizedQuery) return state.processes;
    return state.processes.filter((process) =>
      [process.processo_id, process.latest_document_id, ...process.document_types]
        .join(" ")
        .toLocaleLowerCase("pt-BR")
        .includes(normalizedQuery),
    );
  }, [query, state]);

  return (
    <div className="product-page">
      <PageHero
        icon={FolderKanban}
        title="Meus Processos"
        description="Consulte os processos e as peças documentais disponíveis no corpus demonstrativo."
      />

      <div className="page-toolbar">
        <div className="toolbar-search">
          <Search size={18} />
          <input
            aria-label="Buscar processos"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar por processo ou tipo de documento..."
          />
        </div>
      </div>

      {state.kind === "loading" && <PageSkeleton />}
      {state.kind === "error" && (
        <div className="product-empty">
          <FileText size={28} />
          <h3>Não foi possível carregar os processos.</h3>
          <p>Confira a conexão com o backend e tente novamente.</p>
          <button className="yellow-button" type="button" onClick={load}>
            <RefreshCw size={17} /> Tentar novamente
          </button>
        </div>
      )}
      {state.kind === "ready" && (
        <div className="dashboard-layout">
          <section className="data-panel">
            <div className="process-table process-table-head">
              <span>Processo</span><span>Origem</span><span>Último andamento</span><span>Peças</span><span>Ação</span>
            </div>
            {processes.length === 0 ? (
              <EmptyState hasQuery={Boolean(query.trim())} />
            ) : (
              processes.map((process) => (
                <article className="process-table process-row" key={process.processo_id}>
                  <div>
                    <strong>{process.processo_id}</strong>
                    <p>{formatDocumentType(process.latest_document_type)} mais recente</p>
                    <small>{process.document_types.map(formatDocumentType).join(" · ")}</small>
                  </div>
                  <div><strong>ANEEL</strong><small>Corpus demonstrativo</small></div>
                  <div><strong>{formatDate(process.latest_movement_at)}</strong><small>{process.latest_document_id}</small></div>
                  <div><strong>{process.pieces_count} peças documentais</strong><small>Famílias vinculadas</small></div>
                  <div className="row-actions">
                    <button
                      type="button"
                      onClick={() => navigate(`/processos/${encodeURIComponent(process.processo_id)}`)}
                    >
                      <Eye size={15} /> Ver processo
                    </button>
                  </div>
                </article>
              ))
            )}
          </section>
          <aside className="summary-sidebar">
            <h2>Catálogo demonstrativo</h2>
            <div className="summary-metrics">
              <span><FolderKanban /><strong>{state.processes.length}</strong><small>processos</small></span>
              <span><FileText /><strong>{state.processes.reduce((total, process) => total + process.pieces_count, 0)}</strong><small>peças</small></span>
            </div>
            <p>Estes dados vêm das famílias e relações declarativas carregadas pela fixture local.</p>
          </aside>
        </div>
      )}
    </div>
  );
}

function formatDocumentType(value: string) {
  return value
    .split("_")
    .map((part) => `${part.slice(0, 1).toLocaleUpperCase("pt-BR")}${part.slice(1)}`)
    .join(" ");
}

function formatDate(value: string) {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

function PageSkeleton() {
  return <div className="data-panel"><div className="skeleton wide" />{[1, 2, 3].map((item) => <div className="skeleton table-row" key={item} />)}</div>;
}

function EmptyState({ hasQuery }: { hasQuery: boolean }) {
  return (
    <div className="product-empty">
      <FileText size={28} />
      <h3>{hasQuery ? "Nenhum processo corresponde à busca." : "Nenhum processo disponível."}</h3>
      <p>{hasQuery ? "Revise o número ou o tipo de documento pesquisado." : "O corpus demo ainda não possui relações processuais."}</p>
    </div>
  );
}
