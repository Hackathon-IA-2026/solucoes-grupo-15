import { useState, type FormEvent } from "react";
import { ArrowRight, CalendarDays, FileText, Search, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { searchDocuments, type SearchEnvelope } from "../api/search";
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
 * Cada card de resultado tambem tem os botoes 👍/👎 do Ticket 7 (issue
 * #23) - ver components/FeedbackButtons.tsx.
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
  | { kind: "result"; envelope: SearchEnvelope }
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
      .then((envelope) => setState({ kind: "result", envelope }))
      .catch(() => setState({ kind: "error" }));
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
              <div><p className="eyebrow">Resultados</p><h2>{state.envelope.results.length} família{state.envelope.results.length > 1 ? "s" : ""} encontrada{state.envelope.results.length > 1 ? "s" : ""}</h2></div>
              <p className="result-meta">Corpus {state.envelope.corpus_version} · modo {state.envelope.data_mode}</p>
            </div>
            <ol className="result-list">
              {state.envelope.results.map((result, index) => (
                <li key={result.family_id}>
                  <article className="result-card">
                    <div className="result-rank">{String(index + 1).padStart(2, "0")}</div>
                    <div className="result-main">
                      <div className="result-label-row">
                        <span className="document-type"><FileText size={15} /> {formatDocumentType(result.face.document_type)}</span>
                        <span className="version-pill">Versão vigente</span>
                      </div>
                      <h3>{result.face.document_type} — {result.face.document_version}</h3>
                      <p className="date-line"><CalendarDays size={15} /> Data da versão vigente: {result.face.version_date}</p>
                      <div className="evidence-list">
                        {result.matched_chunks.map((chunk) => (
                          <div className="evidence-item" key={chunk.document_version}>
                            <p>{chunk.excerpt}</p>
                            <span>Trecho na versão {chunk.document_version} — {chunk.is_latest ? "versão mais recente" : "não é a versão mais recente"}</span>
                          </div>
                        ))}
                      </div>
                      <div className="result-actions">
                        <Link className="detail-link" to={`/documents/${result.family_id}`} state={{ matchedChunks: result.matched_chunks }}>
                          Abrir família <ArrowRight size={16} aria-hidden="true" />
                        </Link>
                        <FeedbackButtons requestId={state.envelope.request_id} familyId={result.family_id} />
                      </div>
                    </div>
                  </article>
                </li>
              ))}
            </ol>
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
