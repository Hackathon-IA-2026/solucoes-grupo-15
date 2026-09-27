import { useState, type FormEvent } from "react";
import { ArrowRight, CalendarDays, FileText, Search, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { appendSearchPage, searchDocuments, type SearchEnvelope } from "../api/search";
import { DemoBanner } from "../components/DemoBanner";
import { FeedbackButtons } from "../components/FeedbackButtons";

/**
 * Tela principal do frontend a partir do Ticket 3 (TB1, issue #19).
 *
 * Consulta so POST /v1/search no backend. Os resultados vem inteiramente
 * do mapeamento declarativo do fixture do ai (hackathon/ai/app/fixtures/search_fixtures.json)
 * - nenhum ranking real, embeddings ou busca vetorial acontece aqui nem
 * no backend.
 *
 * As consultas de sugestao abaixo espelham exatamente as chaves
 * declaradas naquele fixture (correspondencia e sempre exata, sem fuzzy
 * matching) - existem so para o usuario nao precisar adivinhar o texto
 * exato; o dado em si continua vindo so da fixture.
 *
 * Desde a issue #93, cada card e um chunk casado (o resultado plano de
 * POST /v1/search, sem agrupamento por familia nem deduplicacao por
 * peca - u4-visualization, issue-64), etiquetado pela versao em que o
 * trecho ocorreu. Os botoes 👍/👎 do Ticket 7 (issue #23, ver
 * components/FeedbackButtons.tsx) votam no proprio chunk do card:
 * document_version + chunk_index do resultado (issues #82/#94).
 */
const SUGGESTED_QUERIES = [
  "padrão de continuidade do fornecimento",
  "auto de infração retificado",
  "processo sei 48500.001234/2024-11",
  "auditoria completa do processo",
] as const;

type SearchState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "result"; query: string; envelope: SearchEnvelope; more: "idle" | "loading" | "error" }
  | { kind: "error" };

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<SearchState>({ kind: "idle" });

  function runSearch(rawQuery: string) {
    const trimmed = rawQuery.trim();
    if (!trimmed) {
      return;
    }
    setQuery(trimmed);
    setState({ kind: "loading" });
    searchDocuments(trimmed)
      .then((envelope) => setState({ kind: "result", query: trimmed, envelope, more: "idle" }))
      .catch(() => setState({ kind: "error" }));
  }

  function loadMore() {
    if (state.kind !== "result" || state.envelope.next_cursor === null) {
      return;
    }
    const current = state;
    const cursor = state.envelope.next_cursor;
    setState({ ...current, more: "loading" });
    searchDocuments(current.query, cursor)
      .then((next) =>
        setState({ ...current, envelope: appendSearchPage(current.envelope, next), more: "idle" }),
      )
      .catch(() => setState({ ...current, more: "error" }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    runSearch(query);
  }

  return (
    <div className="page page-search">
      <DemoBanner />

      <section className="search-intro" aria-labelledby="search-title">
        <div>
          <p className="eyebrow"><Sparkles size={15} /> Pesquisa documental</p>
          <h1 id="search-title">Encontre evidências no contexto certo.</h1>
          <p className="intro-copy">
            Consulte documentos e processos do setor elétrico com rastreabilidade entre
            versões, peças e relações declaradas.
          </p>
        </div>

        <form className="search-form" onSubmit={handleSubmit}>
          <label htmlFor="search-query">Consulta</label>
          <div className="search-input-row">
            <Search size={20} aria-hidden="true" />
            <input
              id="search-query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ex.: auto de infração retificado"
            />
            <button className="primary-button" type="submit">
              Buscar <ArrowRight size={17} aria-hidden="true" />
            </button>
          </div>
        </form>

        <div className="suggestion-row" aria-label="sugestões de consulta">
          <span>Experimente</span>
          {SUGGESTED_QUERIES.map((suggestion) => (
            <button key={suggestion} type="button" onClick={() => runSearch(suggestion)}>
              {suggestion}
            </button>
          ))}
        </div>
      </section>

      <section className="results-section" aria-label="resultados da busca">
        {state.kind === "idle" && (
          <div className="empty-state initial">
            <FileText size={28} aria-hidden="true" />
            <div>
              <h2>Uma busca por vez, uma evidência por contexto.</h2>
              <p>Use uma consulta de demonstração ou escreva a sua para começar.</p>
            </div>
          </div>
        )}
        {state.kind === "loading" && (
          <div className="loading-state"><span className="loading-spinner" aria-hidden="true" /> Buscando...</div>
        )}
        {state.kind === "error" && (
          <div className="empty-state error-state"><h2>Não foi possível concluir a busca.</h2><p>Verifique a conexão com a base e tente novamente.</p></div>
        )}
        {state.kind === "result" && state.envelope.results.length === 0 && (
          <div className="empty-state"><h2>Nenhum resultado para esta consulta demo.</h2><p>Tente uma das consultas sugeridas acima.</p></div>
        )}
        {state.kind === "result" && state.envelope.results.length > 0 && (
          <>
            <div className="results-heading">
              <div><p className="eyebrow">Resultados</p><h2>{state.envelope.total} trecho{state.envelope.total > 1 ? "s" : ""} encontrado{state.envelope.total > 1 ? "s" : ""}</h2></div>
              <p className="result-meta">Corpus {state.envelope.corpus_version} · modo {state.envelope.data_mode}</p>
            </div>
            {state.envelope.stale_corpus && (
              <div className="empty-state stale-corpus" role="status">
                <p>O corpus foi atualizado depois desta busca. Estes resultados continuam sendo do corpus {state.envelope.corpus_version}.</p>
                <button className="primary-button" type="button" onClick={() => runSearch(state.query)}>
                  Refazer a busca
                </button>
              </div>
            )}
            <ol className="result-list">
              {state.envelope.results.map((result, index) => (
                <li key={`${index}-${result.chunk_id}`}>
                  <article className="result-card">
                    <div className="result-rank">{String(index + 1).padStart(2, "0")}</div>
                    <div className="result-main">
                      <div className="result-label-row">
                        <span className="document-type"><FileText size={15} /> {formatDocumentType(result.document_type)}</span>
                      </div>
                      <h3>{formatDocumentType(result.document_type)} — {result.document_id}</h3>
                      <p className="date-line"><CalendarDays size={15} /> Data da versão: {result.version_date}</p>
                      <div className="evidence-list">
                        <div className="evidence-item">
                          <p>{result.excerpt}</p>
                          <span>Trecho na versão {result.document_version}</span>
                        </div>
                      </div>
                      <div className="result-actions">
                        <Link
                          className="detail-link"
                          to={`/documents/${result.family_id}`}
                          state={{ matchedChunks: [{ document_version: result.document_version, excerpt: result.excerpt }] }}
                        >
                          Abrir documento <ArrowRight size={16} aria-hidden="true" />
                        </Link>
                        <FeedbackButtons
                          target={{
                            requestId: state.envelope.request_id,
                            documentVersion: result.document_version,
                            chunkIndex: result.chunk_index,
                          }}
                        />
                      </div>
                    </div>
                  </article>
                </li>
              ))}
            </ol>
            {state.envelope.next_cursor !== null && (
              <div className="load-more-row">
                <button className="primary-button" type="button" onClick={loadMore} disabled={state.more === "loading"}>
                  {state.more === "loading" ? "Carregando..." : "Carregar mais"}
                </button>
                {state.more === "error" && <p className="result-meta">Não foi possível carregar mais resultados. Tente novamente.</p>}
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}

function formatDocumentType(value: string) {
  return value.replaceAll("_", " ");
}

export default SearchPage;
