import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useSession } from "../features/auth/SessionContext";
import { mockPersonas } from "../mocks/personas";
import type { PersonaId } from "../types/product";

export function PersonaPage() {
  const navigate = useNavigate();
  const { selectPersona } = useSession();
  const [selected, setSelected] = useState<PersonaId>("advocacia");

  function continueToApp() {
    selectPersona(selected);
    navigate("/explorar");
  }

  return (
    <main className="persona-page">
      <header className="persona-logo"><img src="/assets/capiwatt-wordmark.png" alt="CapiWatt Lens" /></header>
      <section className="persona-content">
        <h1>Como você quer usar<br />o CapiWatt Lens hoje?</h1>
        <p>Escolha o perfil que melhor combina com sua atividade de hoje.</p>
        <div className="persona-grid">
          {mockPersonas.map((persona) => (
            <button key={persona.id} type="button" className={selected === persona.id ? "persona-card selected" : "persona-card"} onClick={() => setSelected(persona.id)} aria-pressed={selected === persona.id}>
              <span className="persona-image"><img src={persona.image} alt="" /></span>
              {selected === persona.id && <span className="persona-check"><Check size={20} /></span>}
              <strong>{persona.title}</strong><span>{persona.description}</span>
            </button>
          ))}
        </div>
        <button className="yellow-button persona-continue" type="button" onClick={continueToApp}>Continuar <ArrowRight size={23} /></button>
        <button className="persona-back" type="button" onClick={() => navigate("/login")}><ArrowLeft size={19} /> Voltar</button>
      </section>
    </main>
  );
}
