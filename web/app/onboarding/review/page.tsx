import { ReviewView } from "@/components/onboarding/review-views";
import { REVIEW_VIEWS } from "@/components/onboarding/view-names";
import { pickView } from "@/lib/view-param";

export default async function ReviewStep({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  return <ReviewView view={pickView(REVIEW_VIEWS, view)} />;
}
