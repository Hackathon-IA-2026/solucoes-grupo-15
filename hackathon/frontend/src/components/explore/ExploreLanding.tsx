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
          <div><span className="landing-icon"><FolderKanban size={20} /></span><h3>Processos acompanhados</h3><p>Veja atualizações, documentos e prazos dos processos que você segue.</p><button type="button" onClick={() => navigate("/meus-processos")}>Abrir processos <ArrowRight size={15} /></button></div>
          <div><span className="landing-icon green"><BellRing size={20} /></span><h3>Atualizações recentes</h3><p>Três notificações aguardam sua leitura, incluindo um voto juntado.</p><button type="button" onClick={() => navigate("/notificacoes")}>Ver notificações <ArrowRight size={15} /></button></div>
        </aside>
      </div>
    </section>
  );
}
