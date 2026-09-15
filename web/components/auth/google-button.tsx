import { Button } from "@/components/ui/button";
import { GoogleMark } from "@/components/ui/brand";

export function GoogleButton({ label = "Continue with Google" }: { label?: string }) {
  return (
    <Button variant="secondary" full className="h-[50px]">
      <GoogleMark />
      {label}
    </Button>
  );
}
