import { ArrowRight, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { mockFamilies } from "../../mocks/familias";

export function ExploreLanding() {
  const navigate = useNavigate();
  const featuredThemes = mockFamilies.slice(0, 4);

  return (
    <section className="explore-landing" aria-label="Página inicial de exploração">
      <section className="landing-panel landing-families">
        <div className="landing-heading"><div><p className="page-kicker"><Sparkles size={14} /> Temas em destaque</p><h2>Explore por tema</h2></div><button type="button" onClick={() => navigate("/familias")}>Ver temas <ArrowRight size={15} /></button></div>
        <div className="landing-family-grid">
          {featuredThemes.map((family) => (
            <button key={family.id} type="button" className={`landing-family-card ${family.tone}`} onClick={() => navigate("/familias")}>
              <strong>{family.name}</strong><span>{family.documents.toLocaleString("pt-BR")} documentos</span>
            </button>
          ))}
        </div>
      </section>
    </section>
  );
}
