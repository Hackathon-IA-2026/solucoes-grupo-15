import { Bell, BellRing, Eye, FileText, FolderKanban, Search, Star, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { PageHero } from "../components/layout/PageHero";
import { appRepository } from "../services/appRepository";
import type { ProcessDashboard, TrackedProcess } from "../types/product";

export function MyProcessesPage() {
  const [data, setData] = useState<ProcessDashboard | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("Todos");
  const [selected, setSelected] = useState<TrackedProcess | null>(null);
  const [showDocuments, setShowDocuments] = useState(false);
  const [hiddenProcesses, setHiddenProcesses] = useState<string[]>([]);
  const [alerts, setAlerts] = useState<Record<string, boolean>>({});

  useEffect(() => {
    appRepository.getProcessDashboard().then(setData);
  }, []);

  const processes = useMemo(
    () =>
      (data?.processes ?? []).filter((process) => {
        const matchesQuery = `${process.id} ${process.subject} ${process.agency} ${process.tags.join(" ")}`
          .toLowerCase()
          .includes(query.toLowerCase());
        const matchesFilter =
          filter === "Todos" ||
          (filter === "Novas atualizações" && process.unread > 0) ||
          (filter === "Prazo próximo" && process.status === "Prazo próximo") ||
          (filter === "Favoritos" && process.favorite);
        return matchesQuery && matchesFilter && !hiddenProcesses.includes(process.id);
      }),
    [data, query, filter, hiddenProcesses],
  );

  const openProcess = (process: TrackedProcess) => {
    setSelected(process);
    setShowDocuments(false);
  };

  const stopFollowing = (processId: string) => {
    setHiddenProcesses((current) => [...current, processId]);
    setSelected(null);
  };

  return (
    <div className="product-page">
      <PageHero
        icon={FolderKanban}
        title="Meus Processos"
        description="Acompanhe processos SEI, prazos e documentos novos sem consulta manual diária."
      />
      <div className="page-toolbar">
        <div className="toolbar-search">
          <Search size={18} />
          <input
            aria-label="Buscar processos"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar por número, assunto ou órgão..."
          />
        </div>
        <div className="segmented-control">
          {["Todos", "Novas atualizações", "Prazo próximo", "Favoritos"].map((item) => (
            <button type="button" className={filter === item ? "active" : ""} key={item} onClick={() => setFilter(item)}>
              {item}
            </button>
          ))}
        </div>
      </div>

      {!data ? (
        <PageSkeleton />
      ) : (
        <div className="dashboard-layout">
          <section className="data-panel">
            <div className="process-table process-table-head">
              <span>Processo / assunto</span><span>Órgão / origem</span><span>Última atualização</span><span>Status</span><span>Ações</span>
            </div>
            {processes.length === 0 ? (
              <EmptyState text="Nenhum processo acompanhado com esses filtros." />
            ) : (
              processes.map((process) => (
                <article className="process-table process-row" key={process.id}>
                  <div><strong>{process.id} {process.favorite && <Star size={14} fill="currentColor" />}</strong><p>{process.subject}</p><small>{process.tags.join(" · ")}</small></div>
                  <div><strong>{process.agency}</strong><small>{process.origin}</small></div>
                  <div><strong>{process.updatedAt.split(" ")[0]}</strong><small>{process.updatedAt.split(" ")[1]}</small></div>
                  <div><span className={`process-status ${statusTone(process.status)}`}>{process.status}</span>{process.unread > 0 && <small>{process.unread} não lida(s)</small>}</div>
                  <div className="row-actions">
                    <button type="button" onClick={() => openProcess(process)}><Eye size={15} /> Ver processo</button>
                    <button type="button" onClick={() => setAlerts((current) => ({ ...current, [process.id]: !current[process.id] }))}>
                      {alerts[process.id] ? <BellRing size={15} /> : <Bell size={15} />}
                      {alerts[process.id] ? "Alertas ativos" : "Gerenciar alertas"}
                    </button>
                  </div>
                </article>
              ))
            )}
          </section>
          <aside className="summary-sidebar">
            <h2>Resumo dos processos</h2>
            <div className="summary-metrics">
              <span><FileText /><strong>{data.processes.length - hiddenProcesses.length}</strong><small>acompanhados</small></span>
              <span><Bell /><strong>{data.processes.filter((process) => process.unread > 0 && !hiddenProcesses.includes(process.id)).length}</strong><small>com atualização</small></span>
            </div>
            <h3>Atividade recente</h3>
            <ol>{data.activity.map((activity) => <li key={activity.id}><span /><div><strong>{activity.label}</strong><small>{activity.processNumber}</small></div><time>{activity.time}</time></li>)}</ol>
          </aside>
        </div>
      )}

      {selected && (
        <div className="product-modal-backdrop" role="presentation" onMouseDown={() => setSelected(null)}>
          <section className="product-modal" role="dialog" aria-modal="true" aria-labelledby="process-detail-title" onMouseDown={(event) => event.stopPropagation()}>
            <button className="modal-close" type="button" onClick={() => setSelected(null)} aria-label="Fechar"><X /></button>
            <FolderKanban size={28} />
            <h2 id="process-detail-title">{selected.id}</h2>
            <p>{selected.subject}</p>
            <dl className="detail-list">
              <div><dt>Órgão</dt><dd>{selected.agency}</dd></div><div><dt>Origem</dt><dd>{selected.origin}</dd></div>
              <div><dt>Última atualização</dt><dd>{selected.updatedAt}</dd></div><div><dt>Status</dt><dd>{selected.status}</dd></div>
            </dl>
            {showDocuments && (
              <div className="process-document-list">
                <h3>Documentos disponíveis</h3>
                {selected.documents.map((document) => <span key={document}><FileText size={16} /> {document}</span>)}
              </div>
            )}
            <div className="modal-actions">
              <button className="yellow-button" type="button" onClick={() => setShowDocuments(true)}><FileText size={18} /> Abrir documentos</button>
              <button className="danger-outline-button" type="button" onClick={() => stopFollowing(selected.id)}><X size={17} /> Parar de acompanhar</button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function statusTone(status: TrackedProcess["status"]) {
  return status === "Arquivado" ? "green" : status === "Prazo próximo" ? "orange" : "blue";
}

function PageSkeleton() {
  return <div className="data-panel"><div className="skeleton wide" />{[1, 2, 3, 4].map((item) => <div className="skeleton table-row" key={item} />)}</div>;
}

function EmptyState({ text }: { text: string }) {
  return <div className="product-empty"><FileText size={28} /><h3>{text}</h3><p>Ajuste a busca ou os filtros para ver outros resultados.</p></div>;
}
