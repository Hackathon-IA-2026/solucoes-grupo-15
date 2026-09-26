import { Search } from "lucide-react";
import { Link } from "react-router-dom";

import { CapiMark } from "../brand/CapiMark";

export function Brand() {
  return (
    <Link className="cw-brand" to="/explorar" aria-label="CapiWatt Lens">
      <span className="cw-brand-symbol" aria-hidden="true"><CapiMark size={24} /></span>
      <span className="cw-brand-name">Capi<span>Watt</span><small>Lens</small></span>
      <Search className="cw-brand-lens" size={21} aria-hidden="true" />
    </Link>
  );
}
