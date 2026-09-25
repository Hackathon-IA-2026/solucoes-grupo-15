import { ArrowRight, BellRing, FileSearch, FolderKanban, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { mockFamilies } from "../../mocks/familias";

export function ExploreLanding() {
  const navigate = useNavigate();
  const featuredFamilies = mockFamilies.slice(0, 4);

  return (
    <section className="explore-landing" aria-label="Página inicial de exploração">
      <div className="landing-intro">
        <span className="landing-icon"><FileSearch size={21} /></span>
        <div>
          <p className="page-kicker">Comece por uma pergunta</p>
          <h2>Ainda não há uma pesquisa em andamento.</h2>
          <p>Descreva o tema, processo ou dúvida regulatória que você quer investigar. O ranking só aparece depois da sua busca.</p>
        </div>
      </div>
      <div className="landing-grid">
        <section className="landing-panel landing-families">
          <div className="landing-heading"><div><p className="page-kicker"><Sparkles size={14} /> Famílias em destaque</p><h3>Explore por tema</h3></div><button type="button" onClick={() => navigate("/familias")}>Ver todas <ArrowRight size={15} /></button></div>
          <div className="landing-family-grid">
            {featuredFamilies.map((family) => (
              <button key={family.id} type="button" className={`landing-family-card ${family.tone}`} onClick={() => navigate("/familias")}>
                <strong>{family.name}</strong><span>{family.documents.toLocaleString("pt-BR")} documentos</span>
              </button>
            ))}
          </div>
        </section>
        <aside className="landing-panel landing-side">
          <div><span className="landing-icon"><FolderKanban size={20} /></span><h3>Catálogo de processos</h3><p>Consulte as peças e relações processuais disponíveis no corpus demonstrativo.</p><button type="button" onClick={() => navigate("/meus-processos")}>Abrir processos <ArrowRight size={15} /></button></div>
          <div><span className="landing-icon green"><BellRing size={20} /></span><h3>Notificações do corpus</h3><p>Escolha seu escopo para receber alertas sobre novos documentos indexados.</p><button type="button" onClick={() => navigate("/notificacoes")}>Configurar notificações <ArrowRight size={15} /></button></div>
        </aside>
      </div>
    </section>
  );
}
