import { ArrowRight, BarChart3, Coins, Landmark, Leaf, RadioTower, Sparkles, UsersRound, type LucideIcon } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

import { appRepository } from "../../services/appRepository";
import type { Family } from "../../types/product";

const icons: Record<string, LucideIcon> = { leaf: Leaf, coins: Coins, chart: BarChart3, landmark: Landmark, tower: RadioTower, users: UsersRound };

export function ExploreLanding() {
  const navigate = useNavigate();
  const [families, setFamilies] = useState<Family[]>([]);
  useEffect(() => { appRepository.getFamilies().then(setFamilies).catch(() => setFamilies([])); }, []);
  const featuredThemes = families.slice(0, 6);

  return (
    <section className="explore-landing" aria-labelledby="landing-themes-title">
      <section className="landing-panel landing-families">
        <div className="landing-heading"><div><p className="page-kicker"><Sparkles size={14} aria-hidden="true" /> Famílias em destaque</p><h2 id="landing-themes-title">Explore por família</h2></div><button type="button" onClick={() => navigate("/familias")}>Ver todas as famílias <ArrowRight size={15} aria-hidden="true" /></button></div>
        <ul className="landing-family-grid">
          {featuredThemes.map((family) => {
            const Icon = icons[family.icon] ?? Sparkles;
            return (
              <li key={family.id}>
                <button type="button" className={`landing-family-card ${family.tone}`} onClick={() => navigate(`/documents/${encodeURIComponent(family.id)}`)}>
                  <span className="landing-family-icon" aria-hidden="true"><Icon size={20} /></span>
                  <span className="landing-family-text"><strong>{family.name}</strong><span className="landing-family-desc">{family.description}</span><span className="landing-family-count">{family.documents.toLocaleString("pt-BR")} versão(ões)</span></span>
                  <ArrowRight className="landing-family-arrow" size={17} aria-hidden="true" />
                </button>
              </li>
            );
          })}
        </ul>
      </section>
    </section>
  );
}
