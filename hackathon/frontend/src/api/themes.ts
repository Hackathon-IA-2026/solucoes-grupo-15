export type ThemeSummary = {
  id: string;
  name: string;
  description: string;
  tipos_processo: string[];
  status: string;
};

export async function fetchThemes(): Promise<ThemeSummary[]> {
  const r = await fetch('/v1/themes');
  if (!r.ok) throw new Error(`themes failed ${r.status}`);
  return (await r.json()) as ThemeSummary[];
}
