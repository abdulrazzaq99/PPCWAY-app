import * as C from "./campaign-views";
import * as R from "./campaign-review-views";
import type { CampaignView } from "./view-names";

export function CampaignsView({ view }: { view: CampaignView }) {
  const map: Record<CampaignView, () => React.JSX.Element> = {
    list: C.CampaignList,
    detail: C.CampaignDetail,
    settings: C.CampaignSettings,
    keywords: C.Keywords,
    "search-terms": C.SearchTerms,
    "ad-groups": C.AdGroups,
    ads: C.Ads,
    account: C.Account,
    "add-keywords": C.AddKeywords,
    "write-ad": C.WriteAd,
    assets: C.Assets,
    new: C.NewCampaign,
    website: C.Website,
    starter: C.Starter,
    alerts: C.AlertList,
    built: R.Built,
    "searches-why": R.SearchesWhy,
    "ads-rules": R.AdsRules,
    "why-shape": R.WhyShape,
    "pmax-logo": R.PmaxLogo,
    "pmax-month": R.PmaxMonth,
    "summit-plan": R.SummitPlan,
    "summit-list": R.SummitList,
    "summit-leaks": R.SummitLeaks,
    "summit-month": R.SummitMonth,
    "summit-keywords": R.SummitKeywords,
    "summit-ad-test": R.SummitAdTest,
    "summit-results": R.SummitResults,
  };
  const View = map[view];
  return <View />;
}
