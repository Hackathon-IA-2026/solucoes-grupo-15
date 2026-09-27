import { ArrowRight, BarChart3, Coins, Landmark, Leaf, RadioTower, Sparkles, UsersRound, File, type LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { appRepository } from "../../services/appRepository";
import type { Family } from "../../types/product";

const icons: Record<string, LucideIcon> = {
  leaf: Leaf,
  coins: Coins,
  chart: BarChart3,
  landmark: Landmark,
  tower: RadioTower,
  users: UsersRound,
  file: File,
};

export function ExploreLanding() {
  const navigate = useNavigate();
  const [themes, setThemes] = useState<Family[]>([]);

  useEffect(() => {
    let active = true;
    appRepository
      .getFamilies()
      .then((items) => {
        if (active) setThemes(items.slice(0, 6));
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="explore-landing" aria-labelledby="landing-themes-title">
      <section className="landing-panel landing-families">
        <div className="landing-heading">
          <div>
            <p className="page-kicker">
              <Sparkles size={14} aria-hidden="true" /> Temas em destaque
            </p>
            <h2 id="landing-themes-title">Explore por tema</h2>
          </div>
          <button type="button" onClick={() => navigate("/familias")}>
            Ver todos os temas <ArrowRight size={15} aria-hidden="true" />
          </button>
        </div>
        <ul className="landing-family-grid">
          {themes.map((family) => {
            const Icon = icons[family.icon] ?? Sparkles;
            return (
              <li key={family.id}>
                <button
                  type="button"
                  className={`landing-family-card ${family.tone}`}
                  onClick={() => navigate("/familias")}
                >
                  <span className="landing-family-icon" aria-hidden="true">
                    <Icon size={20} />
                  </span>
                  <span className="landing-family-text">
                    <strong>{family.name}</strong>
                    <span className="landing-family-desc">{family.description}</span>
                  </span>
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
