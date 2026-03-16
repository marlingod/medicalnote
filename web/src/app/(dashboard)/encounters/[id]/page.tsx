import { EncounterDetail } from "./encounter-detail";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function EncounterDetailPage({ params }: PageProps) {
  const { id } = await params;
  return <EncounterDetail encounterId={id} />;
}
