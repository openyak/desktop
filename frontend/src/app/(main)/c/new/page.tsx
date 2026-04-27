import { Landing } from "@/components/chat/landing";

interface NewChatPageProps {
  searchParams?: Promise<{ directory?: string | string[] }>;
}

export default async function NewChatPage({ searchParams }: NewChatPageProps) {
  const params = await searchParams;
  const directory = Array.isArray(params?.directory)
    ? params.directory[0]
    : params?.directory;

  return <Landing directoryParam={directory ?? null} />;
}
