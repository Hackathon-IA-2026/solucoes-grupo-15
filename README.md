# CapiWatt Lens

Copiloto de pesquisa regulatória para localizar precedentes e documentos públicos da ANEEL por processo, peça e trecho. O caso de referência é a busca de Carolina por decisões sobre conexões de micro e minigeração distribuída ([fontes e necessidades](hackathon/data/case-1-carolina-mmgd/README.md)).

## Demo

- **AWS:** a infraestrutura da demonstração está definida em [CDK](hackathon/infra/) e na [ADR-0002](hackathon/docs/adr/0002-implantacao-aws-ecs-fargate-cdk.md), mas este repositório não registra uma URL pública estável nem comprova que a stack esteja ativa agora. A saída `CloudFrontUrl` do deploy fornece o endereço quando a stack está no ar.
- **Local:** siga [Como rodar o projeto](#como-rodar-o-projeto). Acesse `http://localhost:5173`, entre com um e-mail e senha de pelo menos quatro caracteres e escolha **Advogados** (o único perfil disponível; os demais aparecem como "Em construção"). Esse login é de demonstração ([implementação](hackathon/frontend/src/pages/LoginPage.tsx)); não representa autenticação Cognito. A configuração local usa [fixtures e `EMBEDDER=fake`](hackathon/docker-compose.yml), portanto a busca local padrão não mede a qualidade da busca vetorial real.

## Tecnologias utilizadas

- **Linguagens e frameworks:** React, TypeScript e Vite no [frontend](hackathon/frontend/package.json); Python 3.12 e FastAPI no [backend](hackathon/backend/pyproject.toml) e no [serviço `ai`](hackathon/ai/pyproject.toml).
- **Dados e IA:** PostgreSQL 16 para catálogo, OpenSearch para índice vetorial e Amazon Bedrock Titan Text Embeddings V2 no [pipeline medido](hackathon/tools/case1_recall/seed_and_measure.py). O [Compose](hackathon/docker-compose.yml) usa `EMBEDDER=fake` por padrão.
- **Implantação:** AWS CDK em Python, ECS Fargate, RDS, OpenSearch, EFS, S3, ALB e CloudFront ([código](hackathon/infra/), [arquitetura](docs/architecture.md)).

## Como rodar o projeto

```bash
git clone https://github.com/Hackathon-IA-2026/solucoes-grupo-15.git
cd solucoes-grupo-15/hackathon
docker compose up --build -d
curl --fail http://localhost:8000/v1/health
# Abra http://localhost:5173 no navegador.
# Ao terminar: docker compose down
```

O retorno esperado do health check é `{"backend":"ok","ai":"ok"}`; os serviços podem levar algum tempo para inicializar. O [Compose](hackathon/docker-compose.yml) sobe frontend, backend, `ai`, PostgreSQL e OpenSearch sem credenciais AWS. O teste ponta a ponta do corpus real tem [pré-requisitos próprios](hackathon/tests_e2e/README.md), inclusive vetores pré-computados fora do Git.

## Pré-requisitos

Git, Docker Engine em execução, Docker Compose v2, `curl` e portas 5173, 8000, 8001, 5432 e 9200 livres ([mapeamento](hackathon/docker-compose.yml)). O fluxo local padrão usa imagens e dependências baixadas durante o build; precisa de acesso à internet na primeira execução.

## Guia para avaliadores

| Critério | Evidência e limite |
| --- | --- |
| Execução técnica e integração | [Arquitetura e contratos](docs/architecture.md), [Compose](hackathon/docker-compose.yml), [suíte e2e](hackathon/tests_e2e/README.md) e [segurança observada](docs/security.md). A URL AWS não é estável neste repositório. |
| Rastreabilidade (Taesa) | [Caminho resposta → fonte e decisão → registro](docs/traceability.md), [corpus do caso 1](hackathon/data/case-1-carolina-mmgd/README.md) e [contratos](requirements/contracts/). O corpus completo não está integralmente no Git. |
| Impacto | [Resultado medido e reprodução](docs/results.md), [gabarito de Carolina](hackathon/data/case-1-carolina-mmgd/README.md). O Recall@3 medido é 2/3 no recorte de dez peças. |
| Inovação | [Pipeline de extração](hackathon/tools/pipeline/README.md), [busca vetorial](hackathon/ai/), [grafo e relações](hackathon/backend/app/ai_relations.py) e [especificação por concerns](docs/specification-with-perspecme.md). |
| Viabilidade | [Decisões e estimativas parciais de custo](requirements/perspec-me/capiwatt-aws-deploy/concerns/i11-cost.md), [implantação](hackathon/docs/adr/0002-implantacao-aws-ecs-fargate-cdk.md) e [limites para piloto](docs/results.md). Não há custo total medido de operação. |

Práticas de engenharia: [acessibilidade](docs/accessibility.md), [segurança](docs/security.md), [evidence packs](docs/evidence-packs.md) e [PerspecMe](docs/specification-with-perspecme.md), incorporadas da [issue #85](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/85) (commit `e4ff188`).

## Metodologia de especificação

A especificação usa [concerns do PerspecMe](docs/specification-with-perspecme.md) para registrar decisões, perguntas abertas e evidências em [Resolution pages](requirements/perspec-me/) e [contratos de fronteira](requirements/contracts/). Issues, ADRs e [evidence packs](docs/evidence-packs.md) ligam decisão, implementação e verificação.

## Licença

Este projeto está sob a licença MIT — veja o arquivo [LICENSE](LICENSE).
