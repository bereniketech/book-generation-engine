import { BookEditorView } from "@/components/BookEditorView";

export default function BookEditorPage({ params }: { params: { id: string } }) {
  return (
    <main className="min-h-screen bg-gray-900">
      <BookEditorView jobId={params.id} />
    </main>
  );
}
