import { PatientDetail } from "./patient-detail";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function PatientDetailPage({ params }: PageProps) {
  const { id } = await params;
  return <PatientDetail patientId={id} />;
}
