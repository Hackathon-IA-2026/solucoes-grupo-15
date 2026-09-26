# CapiWatt

Repositório do Ideathon e Hackathon IA COPPE/UFRJ 2026. Todo o código vive em `hackathon/`; `ideathon/` guarda apenas materiais e documentação.

## Agent skills

### Issue tracker

Issues são rastreadas no GitHub Issues do repo (`EricRLeao1311/CapiWatt`) via `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Cinco labels canônicos padrão (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context, com raiz em `hackathon/` (`hackathon/CONTEXT.md` + `hackathon/docs/adr/`). See `docs/agents/domain.md`.

### Boundary contracts

Contratos de fronteira entre componentes (ex.: backend ↔ serviço vetorial) vivem em `requirements/contracts/`, um arquivo por fronteira — snapshot legível derivado das Concern Resolution pages do `perspec-me` (`requirements/perspec-me/<caso>/concerns/`), nunca a fonte de verdade. Ao editar uma Concern Resolution page ou refreshar o `MAP.md` de um caso de forma que afete uma fronteira já documentada, atualize o arquivo de contrato correspondente na mesma sessão (cada arquivo tem uma seção "Como manter em sincronia").
