import { TemplateDetail } from "./template-detail";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function TemplateDetailPage({ params }: PageProps) {
  const { id } = await params;
  return <TemplateDetail templateId={id} />;
}
