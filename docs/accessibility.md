# Acessibilidade como concern contínuo

Acessibilidade é tratada como uma propriedade a ser revisada ao longo do desenvolvimento do frontend, não como uma etapa isolada no fim do projeto.

## Ferramenta

As revisões utilizam a skill `accessibility-audit`, integrada às ferramentas de agente do time. Ela faz revisão de acessibilidade (não é um scanner automatizado tipo axe-core/Lighthouse) contra uma checklist de 18 critérios de sucesso derivados da **WCAG 2.2**, classificando cada achado por severidade — P0 (impede o uso), P1 (degrada o uso) ou P2 (fricção) — e citando o critério de sucesso correspondente.

## Como entra no fluxo de desenvolvimento

O padrão observado no histórico deste repositório é: uma issue-guarda-chuva pede a revisão completa de uma tela contra WCAG 2.2 usando a skill, e cada achado vira uma issue filha, específica e endereçável — não um documento de auditoria à parte.

Exemplo real: [#44 — "Mapa — correções de acessibilidade WCAG 2.2 do frontend"](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/44) (label `accessibility`, ainda aberta) deu origem a seis issues filhas, cada uma isolando um ou dois critérios de sucesso e já fechadas:

- [#50 — indicadores de foco visíveis e com contraste (SC 1.4.11, 2.4.7)](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/50)
- [#51 — diálogo modal com gerenciamento de foco; menu da conta e popover (SC 2.4.11, 4.1.2)](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/51)
- [#52 — estados ARIA em abas, filtros, segmentados, nós do mapa e disclosure (SC 4.1.2)](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/52)
- [#53 — tokens de texto secundário com contraste mínimo 4,5:1 (SC 1.4.3)](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/53)
- [#54 — layout resistente a texto 200% e tabela semântica (SC 1.4.4, 1.3.1)](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/54)
- [#55 — rótulos visíveis, nomes únicos, erro por campo, anúncios duplicados](https://github.com/Hackathon-IA-2026/solucoes-grupo-15/issues/55)

Todas carregam os labels `accessibility` + `frontend` + `ready-for-agent`, o que as torna Topics específicos o bastante para um agente resolver sem revisão síncrona a cada passo. A issue-mãe (#44) segue aberta como rastreamento agregador enquanto os itens específicos vão sendo fechados individualmente — a revisão avança issue por issue, não como um evento único.

## Por que contínuo e não só no final

Endereçar acessibilidade como issues específicas ligadas a critérios de sucesso (em vez de uma auditoria única ao final) permite fechar cada correção junto do código que a motivou e evita acumular uma dívida de acessibilidade sem visibilidade granular. Fica mais fácil também rastrear qual mudança de código resolveu qual critério — os títulos das issues já citam o SC diretamente.

## Alcance real da revisão

As revisões utilizam critérios derivados da WCAG 2.2 (18 critérios cobertos pela skill, de um total de mais de 50 na especificação completa) e dependem de HTML/URL/screenshot fornecidos no momento da revisão. Isso não equivale a uma certificação de conformidade com WCAG 2.2 nem a uma auditoria automatizada abrangente — é uma revisão especializada, pontual a cada rodada, sobre o que foi de fato examinado.
