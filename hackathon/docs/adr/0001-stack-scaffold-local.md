# 0001 — Stack do scaffold local (frontend, backend, ai)

## Status

Aceita (2026-09-20).

## Contexto

A spec #16 e as issues fechadas #2–#9 e #15 fixam contratos (portas, rotas HTTP, formas de dados) mas nunca uma linguagem ou framework. O plano de execução (`hackathon/docs/CapiWatt_Lens_Plano_de_Execucao_Hackathon.md`, seção "Unidade de trabalho local") só exige três diretórios com Dockerfile próprio (`frontend`, `backend`, `ai`), Docker Compose local, e compatibilidade futura com Lambda + API Gateway + OpenAPI. Isso não é uma decisão pertencente às issues #10–#14 (que tratam de domínio: tipos documentais, gabarito, tarefa concreta, chunking/embeddings) — é uma decisão de implementação necessária para começar a construir os tickets da spec #16, e precisa ser tomada uma única vez para todos os tickets seguirem a mesma base.

## Decisão

- **`backend`** e **`ai`**: Python 3.12 + FastAPI. FastAPI gera OpenAPI nativamente (contratos `/v1/*` e `/internal/v1/*` documentados de graça), é compatível com Lambda via adaptador (Mangum) quando o M4 acontecer, e é a escolha natural para consumir `boto3`/Bedrock depois. Testes com `pytest` + `httpx` (contrato HTTP) e `pytest` puro (contrato do port em processo).
- **`frontend`**: React + TypeScript + Vite. Publicável como estático (S3/CloudFront no M4, fora de escopo agora), rápido para montar uma UI densa e operacional. Testes com Vitest + Testing Library.
- **Catálogo do `backend`**: Postgres (já decidido em #8/#15), acessado via SQLAlchemy + `psycopg`.
- **Índice do `ai`**: container OpenSearch provisionado no Compose (decisão já fechada em #2), mas nenhum ticket do primeiro lote grava ou consulta vetores reais nele — a busca do modo demo é servida por um adapter de fixtures.
- Empacotamento por módulo: cada um com seu próprio `Dockerfile`, gerenciador de dependências (`pip`/`requirements.txt` ou `pyproject.toml` para os módulos Python; `package.json` para o frontend) e suíte de testes independente.

## Consequências

- Todo ticket da spec #16 usa essa mesma base; não é uma decisão a ser revisitada ticket a ticket.
- Trocar o adapter de fixtures por Bedrock/OpenSearch reais, ou o adapter de e-mail por SES real, é troca de adapter dentro da mesma stack — nenhuma mudança de linguagem é esperada.
- Se o time preferir outra stack, esta ADR deve ser suplantada por uma nova antes do próximo lote de tickets.
