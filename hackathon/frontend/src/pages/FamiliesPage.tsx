import { ArrowRight, BarChart3, Coins, Landmark, Leaf, RadioTower, Search, Sparkles, UsersRound, type LucideIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { PageHero } from "../components/layout/PageHero";
import { appRepository } from "../services/appRepository";
import type { Family } from "../types/product";

const icons: Record<string, LucideIcon> = { leaf: Leaf, coins: Coins, chart: BarChart3, landmark: Landmark, tower: RadioTower, users: UsersRound };

export function FamiliesPage() {
  const [families, setFamilies] = useState<Family[] | null>(null);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Family | null>(null);
  useEffect(() => { appRepository.getFamilies().then((items) => { setFamilies(items); setSelected(items[0]); }); }, []);
  const visible = useMemo(() => (families ?? []).filter((family) => `${family.name} ${family.description}`.toLowerCase().includes(query.toLowerCase())), [families, query]);
  return (
    <div className="product-page"><PageHero icon={Sparkles} title="Famílias" description="Navegue pelos grandes temas regulatórios e reúna documentos relacionados em um só lugar." />
      <div className="page-toolbar"><div className="toolbar-search"><Search size={18} /><input aria-label="Pesquisar famílias" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Pesquisar famílias, temas ou palavras-chave..." /></div><div className="segmented-control"><button type="button" className="active">Todas</button><button type="button">Mais acessadas</button><button type="button">Em alta</button></div></div>
      {!families ? <div className="family-grid">{[1,2,3,4,5,6].map((item) => <div className="skeleton family-skeleton" key={item} />)}</div> : visible.length === 0 ? <div className="product-empty"><Sparkles size={28} /><h3>Nenhuma família encontrada.</h3><p>Tente outro tema ou palavra-chave.</p></div> : <div className="families-layout"><section className="family-grid">{visible.map((family) => { const Icon = icons[family.icon]; return <article className={`family-card family-${family.tone}`} key={family.id}><div className="family-visual"><span><Icon size={29} /></span></div><div className="family-body"><h2>{family.name}</h2><p>{family.description}</p><span className="family-status">{family.status}</span><footer><span>{family.documents.toLocaleString("pt-BR")} documentos</span><button type="button" onClick={() => setSelected(family)}>Abrir família <ArrowRight size={16} /></button></footer></div></article>; })}</section><aside className="summary-sidebar family-sidebar">{selected && <div className="featured-family"><span>Família em destaque</span><h2>{selected.name}</h2><p>{selected.description}</p><button type="button">Acessar família <ArrowRight size={16} /></button></div>}<h3>Mais acessadas</h3><ol>{[...(families ?? [])].sort((a,b) => b.documents-a.documents).slice(0,5).map((family,index) => <li key={family.id}><b>{index+1}.</b><span>{family.name}</span><small>{family.documents.toLocaleString("pt-BR")} docs</small></li>)}</ol></aside></div>}
    </div>
  );
}
