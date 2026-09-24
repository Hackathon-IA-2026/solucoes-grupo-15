import { Construction } from "lucide-react";

export function ComingSoonPage({ title, description }: { title: string; description: string }) {
  return <section className="coming-soon-page"><div><Construction size={28} /><p className="page-kicker">Próximo marco</p><h1>{title}</h1><p>{description}</p></div></section>;
}
