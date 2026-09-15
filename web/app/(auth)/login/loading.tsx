import { Skeleton } from "@/components/ui/states";

export default function Loading() {
  return (
    <div className="flex min-h-dvh items-center justify-center p-8">
      <div className="bg-panel border-line w-full max-w-[460px] rounded-[20px] border p-10">
        <Skeleton />
      </div>
    </div>
  );
}
