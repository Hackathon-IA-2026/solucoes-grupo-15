# CapiWatt Lens

> Copiloto regulatório inteligente para o setor elétrico brasileiro — busca semântica em documentos normativos com fontes verificáveis, ranking personalizado por perfil (advogado, engenheiro, pesquisador) e citações rastreáveis.

## Demo

- **Link da demo:** _Em desenvolvimento (hackathon presencial 25-27 de setembro de 2026)_

## Tecnologias utilizadas

- **Linguagens:** Python 3.12, TypeScript
- **Frameworks:** FastAPI (backend e serviço de IA), React 18 + Vite (frontend)
- **Banco de dados:** PostgreSQL 16 (catálogo), OpenSearch 2.17 (índice vetorial)
- **APIs / Serviços externos:** AWS Bedrock (embeddings em produção), fake embedder para desenvolvimento local

## Como rodar o projeto

```bash
# Clone o repositório
git clone https://github.com/Hackathon-IA-2026/solucoes-grupo-15.git
cd solucoes-grupo-15/hackathon

# Suba todos os serviços com Docker Compose
docker compose up

# Acesse:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - AI Service: http://localhost:8001
```

## Pré-requisitos

- Docker e Docker Compose
- Para desenvolvimento local sem Docker:
  - Python 3.12+
  - Node.js 18+

## Arquitetura

```
hackathon/
├── frontend/    # React + Vite — interface de busca e visualização
├── backend/     # FastAPI — API pública /v1/*, orquestra consultas e ingestão
├── ai/          # FastAPI — serviço vetorial /internal/v1/*, embeddings e busca
├── data/        # Documentos dos casos de uso
└── docs/        # Plano de execução e ADRs
```

## Metodologia de especificação

Para especificar e executar este projeto, nos inspiramos no trabalho de Hugo Villamizar, o **PerSpecML**, usando agentes de software engineering e os princípios de **Spec-Driven Development (SDD)**. A especificação — do levantamento de requisitos por múltiplas perspectivas até a execução do código — é conduzida por agentes.

## Licença

Este projeto está sob a licença MIT — veja o arquivo [LICENSE](./LICENSE) para mais detalhes.
