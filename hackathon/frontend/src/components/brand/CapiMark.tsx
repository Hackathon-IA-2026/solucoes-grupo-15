/**
 * Marca do CapiWatt: capivara de frente com capacete de eletricista (como o
 * mascote), sobre selo azul-marinho. Legível também em 16px (ícone da aba).
 */
export function CapiMark({ size = 24, className }: { size?: number; className?: string }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <rect width="64" height="64" rx="14" fill="#031226" />
      <circle cx="17.5" cy="22" r="4.2" fill="#7A4520" /><circle cx="46.5" cy="22" r="4.2" fill="#7A4520" /><path d="M17.5 26C17.5 20 24 17 32 17S46.5 20 46.5 26L47.5 45C47.5 52.5 41 57 32 57S16.5 52.5 16.5 45Z" fill="#A8672F" /><rect x="20" y="37" width="24" height="17" rx="8.5" fill="#7A4520" /><circle cx="24.5" cy="30" r="2.6" fill="#031226" /><circle cx="39.5" cy="30" r="2.6" fill="#031226" /><ellipse cx="27.5" cy="43.5" rx="2.1" ry="1.4" fill="#031226" /><ellipse cx="36.5" cy="43.5" rx="2.1" ry="1.4" fill="#031226" /><path d="M15 22C15 12 22.5 6 32 6S49 12 49 22Z" fill="#FFC400" /><rect x="11.5" y="20" width="41" height="4.6" rx="2.3" fill="#FFC400" /><path d="M33.5 9L28.5 16H32L30.5 21L36 13.5H32.5Z" fill="#031226" />
    </svg>
  );
}
