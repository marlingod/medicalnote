import { EditTemplateForm } from "./edit-template-form";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function EditTemplatePage({ params }: PageProps) {
  const { id } = await params;
  return <EditTemplateForm templateId={id} />;
}
