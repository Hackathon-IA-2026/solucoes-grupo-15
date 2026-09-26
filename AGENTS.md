# CapiWatt

Repositório do Ideathon e Hackathon IA COPPE/UFRJ 2026. Todo o código vive em `hackathon/`; `ideathon/` guarda apenas materiais e documentação.

## Escopo de repositório e autorização (LEIA PRIMEIRO)

- Repositório ativo: org **`Hackathon-IA-2026`** no GitHub (remote local aponta para `Hackathon-IA-2026/solucoes-grupo-15`), que substituiu o repositório antigo (`EricRLeao1311/CapiWatt`). O repo antigo está **descontinuado** — nenhum agente deve ler ou escrever issues/PRs/labels lá, salvo pedido explícito do dono do repo.
- Qualquer ação que toque um remoto — `git push`, `gh issue`/`gh pr` (criar, comentar, fechar, mudar label), etc. — em **qualquer** repositório, só deve ser executada com autorização explícita do dono para aquela ação específica. Isso vale para todos os agentes (Claude, Codex, ou qualquer outro), não é uma permissão implícita por ter sido liberada uma vez.

## Agent skills

### Issue tracker

Issues são rastreadas no GitHub Issues do repositório novo (`Hackathon-IA-2026/solucoes-grupo-15`) via `gh` — ver `docs/agents/issue-tracker.md`. Esse fluxo substituiu o rastreamento no repo antigo (`EricRLeao1311/CapiWatt`, descontinuado); não usar `gh` contra o repo antigo.

### Triage labels

Cinco labels canônicos padrão (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context, com raiz em `hackathon/` (`hackathon/CONTEXT.md` + `hackathon/docs/adr/`). See `docs/agents/domain.md`.

### Boundary contracts

Contratos de fronteira entre componentes (ex.: backend ↔ serviço vetorial) vivem em `requirements/contracts/`, um arquivo por fronteira — snapshot legível derivado das Concern Resolution pages do `perspec-me` (`requirements/perspec-me/<caso>/concerns/`), nunca a fonte de verdade. Ao editar uma Concern Resolution page ou refreshar o `MAP.md` de um caso de forma que afete uma fronteira já documentada, atualize o arquivo de contrato correspondente na mesma sessão (cada arquivo tem uma seção "Como manter em sincronia").
