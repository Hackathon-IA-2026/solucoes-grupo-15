import { ArrowLeft, ArrowRight, Check, Zap } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useSession } from "../features/auth/SessionContext";
import { mockPersonas } from "../mocks/personas";
import type { PersonaId } from "../types/product";

export function PersonaPage() {
  const navigate = useNavigate();
  const { selectPersona } = useSession();
  const [selected, setSelected] = useState<PersonaId | null>(null);

  function continueToApp() {
    if (!selected) return;
    selectPersona(selected);
    navigate("/explorar");
  }

  return (
    <main className="persona-page">
      <header className="persona-logo" aria-label="CapiWatt Lens">
        <span className="persona-logo-symbol"><Zap size={27} fill="currentColor" aria-hidden="true" /></span>
        <span className="persona-logo-name">Capi<span>Watt</span><small>Lens</small></span>
      </header>
      <section className="persona-content">
        <p className="persona-kicker">Comece pelo seu contexto de trabalho</p>
        <h1>Como você quer usar o CapiWatt Lens hoje?</h1>
        <p className="persona-lead">Seu perfil organiza as sugestões e o jeito de explorar processos, documentos e normas.</p>
        <div className="persona-grid">
          {mockPersonas.map((persona) => (
            <button key={persona.id} type="button" className={`persona-card persona-${persona.id} ${selected === persona.id ? "selected" : ""}`} onClick={() => setSelected(persona.id)} aria-pressed={selected === persona.id}>
              <span className="persona-image"><img src={persona.image} alt="" /></span>
              {selected === persona.id && <span className="persona-check"><Check size={20} /></span>}
              <span className="persona-copy"><small>{persona.label}</small><strong>{persona.title}</strong><span>{persona.description}</span></span>
            </button>
          ))}
        </div>
        <button className="yellow-button persona-continue" type="button" onClick={continueToApp} disabled={!selected}>Continuar <ArrowRight size={23} /></button>
        <button className="persona-back" type="button" onClick={() => navigate("/login")}><ArrowLeft size={19} /> Voltar</button>
      </section>
    </main>
  );
}
