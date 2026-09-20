import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { searchDocuments, type SearchEnvelope } from "../api/search";

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
    <div>
      <p role="status" aria-label="aviso de dados demo">
        Dados de demonstração/fixture — este corpus é fictício, não representa
        casos reais e não deve ser tratado como tal.
      </p>

      <form onSubmit={handleSubmit}>
        <label htmlFor="search-query">Buscar</label>
        <input
          id="search-query"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Digite uma consulta demo..."
        />
        <button type="submit">Buscar</button>
      </form>

      <div aria-label="sugestões de consulta">
        {SUGGESTED_QUERIES.map((suggestion) => (
          <button key={suggestion} type="button" onClick={() => runSearch(suggestion)}>
            {suggestion}
          </button>
        ))}
      </div>

      <section aria-label="resultados da busca">
        {state.kind === "loading" && <p>Buscando...</p>}
        {state.kind === "error" && <p>Não foi possível concluir a busca.</p>}
        {state.kind === "result" && state.envelope.results.length === 0 && (
          <p>Nenhum resultado para esta consulta demo.</p>
        )}
        {state.kind === "result" && state.envelope.results.length > 0 && (
          <ul>
            {state.envelope.results.map((result) => (
              <li key={result.family_id}>
                <article>
                  <h3>
                    {result.face.document_type} — {result.face.document_version}
                  </h3>
                  <p>Data da versão vigente: {result.face.version_date}</p>
                  <Link to={`/documents/${result.family_id}`}>Ver família</Link>
                  <ul>
                    {result.matched_chunks.map((chunk) => (
                      <li key={chunk.document_version}>
                        <p>{chunk.excerpt}</p>
                        <p>
                          trecho na versão {chunk.document_version} —{" "}
                          {chunk.is_latest
                            ? "versão mais recente"
                            : "não é a versão mais recente"}
                        </p>
                      </li>
                    ))}
                  </ul>
                </article>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default SearchPage;
