# Frontend x Backend - integrações futuras

Este documento registra capacidades necessárias para substituir os mocks do protótipo. Ele não define novos endpoints nem altera contratos existentes. O backend, a IA, o banco e a infraestrutura permaneceram inalterados nesta entrega.

## Estratégia de integração

A experiência nova consome a interface `AppRepository`, implementada hoje por `MockAppRepository` em `src/services/appRepository.ts`. Uma integração futura deve criar outro provider dessa interface e mapear respostas reais para os tipos de `src/types/product.ts`, sem acoplar as páginas ao transporte HTTP.

As integrações antigas continuam disponíveis nas rotas de compatibilidade e em `src/api/`.

## Busca e ranking de precedentes

### Necessidade futura

Receber uma consulta em linguagem natural, filtros e objetivo jurídico; retornar processos ranqueados com aderência, justificativa, metadados e documentos disponíveis. O cálculo de aderência e a justificativa precisam ser auditáveis.

### Frontend atual

Usa `mockExploreData`, incluindo o Top 3 de MMGD, percentuais, motivos do ranking, tags e documentos-chave. Não existe cálculo de similaridade, calibração de limiar, busca vetorial real ou validação de qualidade.

### Backend

Não alterado.

## Cobertura e lacunas da pesquisa

### Necessidade futura

Avaliar a cobertura jurídica, regulatória, técnica e econômica do conjunto encontrado, além de identificar evidências ausentes ou desatualizadas.

### Frontend atual

Percentuais e lacunas são mockados. O CTA simula uma nova busca, resolve uma lacuna e atualiza a cobertura apenas no estado local.

### Backend

Não alterado.

## Processos acompanhados e documentos

### Necessidade futura

Listar processos seguidos, status, última movimentação, unidade responsável, não lidos e documentos. Também será necessário persistir seguir/parar de seguir e preferências de alerta.

### Frontend atual

Usa `mockProcessDashboard`. Busca, filtros, alertas, abertura de documentos e a ação de parar de acompanhar funcionam apenas durante a sessão local.

### Backend

Não alterado.

## Monitoramento e notificações

### Necessidade futura

Detectar novo andamento no SEI/SICNET em até duas horas e gerar notificação com data, número, resumo e PDF ou indicação de acesso restrito. O envio por e-mail deve respeitar preferências persistidas e oferecer rastreabilidade de entrega.

### Frontend atual

Usa `mockNotifications`. Marcar como lida, filtros e preferências são apenas interações locais; nenhum e-mail é enviado.

### Backend

Não alterado.

## PDFs e disponibilidade documental

### Necessidade futura

Catalogar o arquivo original, fonte oficial, número SEI/SICNET, tipo documental, data, processo e situação de acesso. Downloads devem entregar PDFs individuais e informar claramente quando o documento estiver restrito ou indisponível.

### Frontend atual

Exibe nomes e disponibilidade mockados. Os PDFs reais fornecidos para o corpus não foram publicados nem enviados por esta interface.

### Backend

Não alterado.

## Famílias regulatórias

### Necessidade futura

Fornecer famílias, contagem de documentos, atividade recente, metadados e documentos relacionados, com busca e ordenação.

### Frontend atual

Usa `mockFamilies`. Seleção, busca e destaques não são persistidos.

### Backend

Não alterado.

## Parecer conclusivo

### Necessidade futura

Montar uma síntese rastreável a partir das evidências selecionadas, preservando citações, valores, datas, fundamentos e grau de confiança. Exportação e compartilhamento exigirão formato e controle de acesso definidos.

### Frontend atual

Usa `mockOpinion`. Conteúdo, confiança, cobertura e abas são demonstrativos; exportação gera somente um arquivo de texto local e não há geração real por IA.

### Backend

Não alterado.

## Mapas e relações

### Necessidade futura

Entregar relações declarativas entre processo, documentos, decisão e normas, com origem e evidência de cada vínculo.

### Frontend atual

O mapa é uma visualização mockada e interativa. Não infere relações nem consulta o grafo existente do backend.

### Backend

Não alterado.

## Sessão, personas e conta

### Necessidade futura

Integrar autenticação, autorização, usuário, persona ativa e preferências sem alterar os fluxos já definidos pelo backend.

### Frontend atual

Login e sessão são locais. Qualquer e-mail preenchido e senha com pelo menos quatro caracteres iniciam a demonstração; não há transmissão de credenciais.

### Backend

Não alterado.

## Critérios antes de trocar o provider

- Confirmar os contratos com o time responsável pelo backend.
- Criar testes de contrato no frontend para os mapeamentos.
- Manter o provider mockado para demonstração e desenvolvimento isolado.
- Tratar loading, vazio, erro, restrição documental e indisponibilidade em cada integração.
- Validar números de processo, datas, distribuidoras, valores, resultado do recurso e referências normativas como campos críticos.
- Não inferir dados ausentes: sinalizar a lacuna explicitamente.
