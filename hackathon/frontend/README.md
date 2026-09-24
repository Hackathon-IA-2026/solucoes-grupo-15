# CapiWatt Lens - frontend

Protótipo React/Vite da experiência do CapiWatt Lens. O fluxo principal funciona integralmente com dados mockados e não depende do backend para login, escolha de persona, ranking, processos, famílias, parecer, mapa ou notificações.

## Rodar localmente

Requisitos: Node.js 20+ e npm.

```bash
npm ci
npm run dev
```

Acesse `http://localhost:5173`. No login de demonstração, informe qualquer e-mail e uma senha com pelo menos quatro caracteres.

## Fluxo principal

1. `/login`
2. `/escolher-perfil`
3. Selecione **Advocacia regulatória** e continue para `/explorar`.
4. Navegue por `/meus-processos`, `/familias`, `/mapas-relacoes`, `/parecer-conclusivo` e `/notificacoes`.

As rotas preexistentes que consomem APIs reais foram preservadas em `/consulta-api`, `/integracoes/notificacoes`, `/documents/:familyId` e `/processos/:processoId`.

## Verificação

```bash
npm run lint
npm test
npm run build
```

## Estrutura principal

- `src/components/layout/`: shell, topbar, sidebar, marca e hero compartilhado.
- `src/components/explore/`: ranking explicável e análise de cobertura.
- `src/features/auth/`: sessão e guards do fluxo mockado.
- `src/mocks/`: dados centralizados da demonstração.
- `src/services/appRepository.ts`: contrato e provider dos mocks.
- `src/pages/`: páginas novas e telas de compatibilidade com as APIs existentes.
- `src/styles/`: tokens e estilos responsivos do produto.
- `public/assets/`: imagens do handoff e panorama autoral do setor elétrico.

As integrações futuras estão registradas em [FRONTEND_BACKEND_GAPS.md](./FRONTEND_BACKEND_GAPS.md).
