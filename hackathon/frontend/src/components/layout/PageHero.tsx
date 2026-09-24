import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function PageHero({ icon: Icon, title, description, children }: { icon: LucideIcon; title: string; description: string; children?: ReactNode }) {
  return (
    <header className="page-hero">
      <div><p className="page-kicker"><Icon size={15} /> CapiWatt Lens</p><h1>{title}</h1><p>{description}</p></div>
      {children && <div className="page-hero-actions">{children}</div>}
    </header>
  );
}
