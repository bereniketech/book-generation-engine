import { ExportView } from "@/components/ExportView";

export default function ExportPage({ params }: { params: { id: string } }) {
  return (
    <main className="min-h-screen bg-gray-900">
      <ExportView jobId={params.id} />
    </main>
  );
}
