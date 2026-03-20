import { Suspense } from "react";
import { MobileTaskClient } from "./task-client";

export async function generateStaticParams() {
  return [{ id: "_" }];
}

export default async function MobileTaskPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <Suspense fallback={null}>
      <MobileTaskClient sessionId={id} />
    </Suspense>
  );
}
