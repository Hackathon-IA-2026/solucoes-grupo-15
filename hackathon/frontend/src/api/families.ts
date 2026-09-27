export type FamilySummary = {
  family_id: string;
  document_type: string;
  versions_count: number;
};
export async function fetchFamilies(): Promise<FamilySummary[]> {
  const r = await fetch('/v1/families');
  if (!r.ok) throw new Error(`families failed ${r.status}`);
  return (await r.json()) as FamilySummary[];
}
