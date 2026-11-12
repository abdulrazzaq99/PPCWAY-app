# Google Ads API v25: campaign creation map for PPCWay

Researched 12 November 2026 against developers.google.com/google-ads/api (v25 reference pages, guides and release notes), with Google Ads Help used only where the API docs give no number. Written for the PPCWay product team, which must rebuild Google's "New campaign" flow through the API. Someone else is documenting the UI screens; this document covers the API only.

PPCWay calls `https://googleads.googleapis.com/v25` over REST and launches a campaign as one atomic `GoogleAdsService.Mutate` with temporary resource names, checked first with `validateOnly`. The "PPCWay sends today" column was checked against `backend/src/ppcway/builder/campaign.py` and `backend/src/ppcway/gateway/google.py`, and against `docs/reference/google-ads-api-v25-coverage.html`.

**How to read the tables.** Field paths use the snake_case names from the reference (`campaign.advertising_channel_type`); REST JSON uses lowerCamelCase (`advertisingChannelType`). "Level" is where the setting lives: request, operation, customer (account), campaign, budget, ad group, ad, asset group or shared set. Anything not confirmed on a v25 reference page is marked **(unconfirmed)**. Where a limit comes only from Google Ads Help, the source column says so by its support.google.com URL.

## What to act on first

1. **Remove the language criterion from the Search builder.** Since late September 2026, Google rejects `campaign_criterion.language` on Search campaigns with `ContextError.OPERATION_NOT_PERMITTED_FOR_CONTEXT`, in every API version. PPCWay sends one on every launch, and because the launch is atomic, that one operation fails the whole campaign (section 3; https://developers.google.com/google-ads/api/docs/deprecations).
2. **Developer tokens are sunset.** Google says developer tokens "are deprecated and have been sunset" (9 September 2026); the header is ignored and the access level now comes from the Google Cloud project (section 10.1; https://developers.google.com/google-ads/api/docs/api-policy/developer-token).
3. **v26 is out and v25 sunsets in August 2027.** v26 shipped on 14 October 2026; v23 to v26 are live (section 10; https://developers.google.com/google-ads/api/docs/sunset-dates).
4. **Customer acquisition moved.** `CampaignLifecycleGoal` and `CustomerLifecycleGoal` were removed in v25. New customer acquisition now lives on `Goal` and `CampaignGoalConfig`, which cannot go in the atomic Mutate (sections 2.3 and 7).
5. **Campaign-level broad match is gone; AI Max replaces it.** `campaign.keyword_match_type = BROAD` fails since 3 August 2026. AI Max for Search arrived in v21 and is switched on with `campaign.ai_max_setting.enable_ai_max` (sections 2.4, 2.5 and 10).
6. **The gateway shows only the first error.** A validate-only call can return many errors; the merchant sees one at a time (section 1.8).
7. **Search ad previews do not exist in the API.** `ShareablePreviewService` covers Performance Max asset groups and YouTube only, and Google's AI text and image generator (`AssetGenerationService`) is still a closed beta (section 8).

## Gap summary

| Area | What PPCWay sends today | What Google's full flow can set through the API | Section |
|---|---|---|---|
| Request mechanics | Atomic Mutate, temporary ids, `validateOnly` then real call | Same, plus policy exemptions on resend and `responseContentType` | 1 |
| Budget | Daily amount, standard delivery, not shared, unique name | Total (lifetime) budgets with `CUSTOM_PERIOD` and an end date; shared budgets | 2.1 |
| Campaign | SEARCH, enabled, networks, presence location option, EU declaration | Start and end date and time, URL options, AI Max, text guidelines, Performance Max brand settings | 2 |
| Bidding | Maximize clicks or maximize conversions, no targets | Target CPA, maximize conversion value with target ROAS, target impression share, manual CPC, portfolio strategies | 2.2 |
| Criteria | Locations, one language (now rejected), phrase-match campaign negatives | Radius, location groups, ad schedule, devices and bid modifiers, IP exclusions, shared negative lists, audiences in observation, brand lists | 3 |
| Ad groups and ads | Search standard ad groups, phrase keywords, responsive search ads with headlines, descriptions and a final URL | Exact and broad keywords, ad group negatives, pinning, `path1` and `path2`, keyword bids, URL options | 4 |
| Assets | None | Sitelinks, callouts, snippets, call, price, promotion, lead form, business name, logo, images, location | 5 |
| Performance Max | None | Asset groups, asset minimums, signals, search themes, listing groups, brand and URL exclusions | 6 |
| Conversion goals | None (account defaults apply) | Campaign goal overrides in the same Mutate; custom goals; new customer acquisition in a second call | 7 |
| Helpers | Keyword ideas, place suggestions | Forecasts, recommendations for a campaign not yet created, brand suggestions, AI asset generation (beta) | 8 |
| Other campaign types | None | Demand Gen, Display, Shopping, App creatable; Video, Local Services, Smart not | 9 |

## 1. Creation mechanics

### 1.1 GoogleAdsService.Mutate: request and response

`Mutate` "executes mutate and actions operations" across resource types in one synchronous call. By default it is atomic: either every operation applies, or the whole request fails and nothing is applied ([mut], [bulk]). With `validate_only` the request is checked but not run, and "Mutates only return errors, not results": a clean check returns empty `results`, and a failed one returns a `GoogleAdsFailure` ([req], [struct]). Contiguous operations of the same type go to the backend together, so keep same-type operations next to each other; interleaving slows the request and "can lead to request timeouts on large batches" ([mbp], [mut]).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Customer | `MutateGoogleAdsRequest.customer_id`; REST `POST https://googleads.googleapis.com/v25/customers/{customerId}/googleAds:mutate` (the REST reference page for this method did not load, so the path is **(unconfirmed)** from the reference, but it follows the `:mutate` pattern in [restmut] and PPCWay's working calls) | Numeric string, required | Request | All | [req] | Yes |
| Operations | `mutate_operations[]` (REST `mutateOperations`) | `MutateOperation` oneof with 64 kinds. For creation: `campaign_budget_operation`, `bidding_strategy_operation`, `campaign_operation`, `campaign_criterion_operation`, `campaign_asset_operation`, `campaign_asset_set_operation`, `campaign_shared_set_operation`, `shared_set_operation`, `shared_criterion_operation`, `ad_group_operation`, `ad_group_criterion_operation`, `ad_group_ad_operation`, `ad_group_asset_operation`, `asset_operation`, `asset_group_operation`, `asset_group_asset_operation`, `asset_group_signal_operation`, `asset_group_listing_group_filter_operation`, `campaign_conversion_goal_operation`, `conversion_goal_campaign_config_operation`. Action operations: `book_campaigns_operation`, `quote_campaigns_operation` | Request | All | [req], [mop] | Yes (budget, campaign, campaign criterion, ad group, ad group criterion, ad group ad) |
| Partial failure | `partial_failure` (`partialFailure`) | bool, default false. "If false, all operations will be carried out in one transaction if and only if they are all valid" | Request | All | [req] | Yes, `false` |
| Validate only | `validate_only` (`validateOnly`) | bool, default false | Request | All | [req], [struct] | Yes, `true` first, then `false` |
| Response content | `response_content_type` (`responseContentType`) | `RESOURCE_NAME_ONLY`, `MUTABLE_RESOURCE`. Unset returns names only; `MUTABLE_RESOURCE` makes the payload larger | Request | All | [req], [rct], [mbp] | No (default) |
| Temporary resource name | `<x>_operation.create.resource_name` with a negative id, for example `customers/123/campaignBudgets/-1` | Negative integer, never 0 | Operation | All | [mut], [mbp] | Yes |
| Per-operation result | `MutateGoogleAdsResponse.mutate_operation_responses[]`, one `<x>_result` per operation (for example `campaign_result.resource_name`) | In request order | Response | All | [resp], [mopr] | Yes, read |
| Partial failure error | `MutateGoogleAdsResponse.partial_failure_error` (`google.rpc.Status`) | Only when `partial_failure` is true and every error sits inside the operations; authorisation and similar errors fail the whole call | Response | All | [resp] | Not applicable |

The operation names in the second row other than those PPCWay sends were confirmed as `MutateOperation` members on [mop]; the asset group, conversion goal and asset set entries are listed because sections 6 and 7 rely on them.

### 1.2 Temporary resource names and operation order

- A negative number where the server would put an id creates a temporary name. Temporary names "are not remembered across requests", and "there's no limit to the number of temp names in a request" ([mut]).
- Each temporary id must be unique across all resource types in the request. Reusing one gives `NewResourceCreationError.DUPLICATE_TEMP_IDS` ([mbp], [tmp], [nrc]).
- Order matters: "Resources must be created with a temp name before the name can be reused". The budget comes before the campaign, and every parent before its children ([mut], [mbp]).
- If a parent fails validation, each child fails with `NewResourceCreationError.TEMP_ID_RESOURCE_HAD_ERRORS`. Those are noise; fix the parent's own error first ([mbp], [nrc]).
- Temporary ids work only in `create` and in references to a parent created earlier in the same request. Using one in a `remove` gives `RequestError.RESOURCE_NAME_MALFORMED` ([tmp]). Setting the numeric `id` field on a create gives `NewResourceCreationError.CANNOT_SET_ID_FOR_CREATE` ([nrc]). Leave `resource_name` out when nothing refers to the resource ([tmp]).
- One resource may be changed only once per request: `MutateError.ID_EXISTS_IN_MULTIPLE_MUTATES`, and for ads `AdGroupAdError.RESOURCE_REFERENCED_IN_MULTIPLE_OPS` ([mute], [agae]).
- Google's guides give examples (campaigns, ad groups, ads, criteria, assets, asset groups) but no complete list of resources that accept temporary ids **(unconfirmed beyond those examples)** ([tmp]).
- Do not combine temporary ids with `partial_failure` set to true: "You shouldn't use partial failure for requests with interdependent operations" ([pf]).

### 1.3 validate_only

- Google's testing guide describes it as a way "to verify that the request is structured correctly and does not violate policies" ([test]).
- It is not supported on `SearchStream`, nor (from v25) on generating Performance Max from a Smart campaign (`SmartCampaignError.VALIDATE_ONLY_GENERATE_PMAX_NOT_SUPPORTED`). The general refusal is `MutateError.RESOURCE_DOES_NOT_SUPPORT_VALIDATE_ONLY` ([test], [mute]).
- `BatchJobService` has no validate-only mode ([mov]).
- Whether validate-only operations count against the daily quota is **(unconfirmed)**. The quota page says only that requests rejected with a `GoogleAdsFailure` still count ([quotas]).
- Passing validation does not mean the ad is approved. Review happens after creation and is read from `policy_summary` (1.5).

### 1.4 When to use BatchJobService instead

Batch jobs run asynchronously, "without synchronously waiting for the operations to complete". Google says they reduce the number of requests and retry operations that fail on transient errors, but "doesn't guarantee improved performance" ([bov]). Every operation in a batch job runs with partial failure, except atomic sub-batches such as a Performance Max asset group with its assets, or a listing group tree, and completed operations are not rolled back if others fail ([bov], [bbp]).

Temporary ids carry across successive `AddBatchJobOperations` calls in the same job, but not to other jobs ([tmp], [abjo]). Results come back in upload order ([bbp]). `CustomerOperation`, `BookCampaignsOperation` and `QuoteCampaignsOperation` cannot go in a batch job ([bov]).

The flow is `MutateBatchJob` (creates the job, status `PENDING`), then `AddBatchJobOperations` (`resource_name`, `mutate_operations[]`, `sequence_token`, omitted on the first call), then `RunBatchJob` (returns a long-running operation), then poll `Operations.GetOperation` or `batch_job.status` until `DONE`, then `ListBatchJobResults` ([bflow], [abjo]). Each poll costs one quota operation, a running job cannot be cancelled, and `BatchJobMetadata.execution_limit_seconds` sets an approximate time cap with no default ([bflow], [bjm], [bbp]).

For PPCWay: one Search or Performance Max campaign is a few hundred operations at most, far under the 10,000 operation limit of `Mutate`. A batch job only pays off for bulk builds over 10,000 operations or fire-and-forget jobs, and it costs PPCWay its all-or-nothing launch. Stay on `Mutate`.

### 1.5 Policy checks before launch and exemptions

Through `Mutate`, a policy problem comes back as an error from either a validate-only call or a real call. `PolicyFindingError` and `PolicyViolationError` are both on the Mutate list of thrown errors ([mut]).

- **Ads:** `PolicyFindingError.POLICY_FINDING`, "disapproved since the policy summary includes policy topics of type PROHIBITED". The detail is in `GoogleAdsError.details.policy_finding_details.policy_topic_entries[]` ([pfe], [pfd]).
- **Keywords:** `PolicyViolationError.POLICY_ERROR`. The detail is in `details.policy_violation_details` (`key`, `is_exemptible`, `external_policy_name`, `external_policy_description`) ([pve], [pvd]).

Google's sample runs the ad mutate with `validate_only` true, keeps the `POLICY_FINDING` errors and reads their topics ([validad]). To ask for an exemption, resend the same operation with the exemption fields filled in. For ads, copy each `PolicyTopicEntry.topic` into `policy_validation_parameter.ignorable_policy_topics`. For keywords, copy each exemptible `key` into `exempt_policy_violation_keys` ([pex], [pexads]). Exempted resources "will be saved" but do not serve until a policy change, a re-review or a change in advertiser certificates allows it ([pvp], [agco]). Only violations with `is_exemptible` true can be exempted ([pvp], [pvd]). Google's samples send ad exemptions through `AdGroupAdService.MutateAdGroupAds`; the same fields sit on the `MutateOperation` sub-operations, so they work in the atomic request too ([mop]).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Ad exemption | `AdGroupAdOperation.policy_validation_parameter.ignorable_policy_topics[]` (`AdOperation.policy_validation_parameter` for ad updates) | Strings equal to `PolicyTopicEntry.topic`. Must be empty if `exempt_policy_violation_keys` is set | Operation | Any with ads (Google's sample is a responsive search ad) | [agao], [pvp], [pexads] | No |
| Ad exemption by key | `AdGroupAdOperation.policy_validation_parameter.exempt_policy_violation_keys[]` | `PolicyViolationKey`; `violating_text` "must be specified for ad exemptions". Some ad types refuse it | Operation | Ad types that support it **(unconfirmed which)** | [pvp], [pvk], [pvpe] | No |
| Keyword exemption | `AdGroupCriterionOperation.exempt_policy_violation_keys[]` | `PolicyViolationKey {policy_name, violating_text}`. Leaving out `violating_text` exempts the whole policy | Operation | SEARCH (keywords) | [agco], [pvk] | No |
| Topic entry type | `PolicyTopicEntry.type` (also `topic`, `evidences[]`, `constraints[]`) | `PROHIBITED`, `LIMITED`, `FULLY_LIMITED`, `DESCRIPTIVE`, `BROADENING`, `AREA_OF_INTEREST_ONLY` | Error detail and read | All | [pte], [ptet] | No |
| Ad approval after creation | `ad_group_ad.policy_summary.approval_status` | `APPROVED`, `APPROVED_LIMITED`, `AREA_OF_INTEREST_ONLY`, `DISAPPROVED` | Read (GAQL) | All with ads | [agaps], [pas], [agaf] | No (PPCWay reads approval for Otto, not at launch) |
| Ad review stage | `ad_group_ad.policy_summary.review_status` | `REVIEW_IN_PROGRESS`, `REVIEWED`, `UNDER_APPEAL`, `ELIGIBLE_MAY_SERVE` | Read | All with ads | [agaps], [prs] | No |
| Ad findings | `ad_group_ad.policy_summary.policy_topic_entries` | `PolicyTopicEntry[]` | Read | All with ads | [agaps], [agaf] | No |
| Keyword approval | `ad_group_criterion.approval_status`, `ad_group_criterion.disapproval_reasons[]` | `APPROVED`, `DISAPPROVED`, `PENDING_REVIEW`, `UNDER_REVIEW` | Read | SEARCH | [agc], [agcas] | No |

### 1.6 EU political advertising declaration

`campaign.contains_eu_political_advertising` takes `CONTAINS_EU_POLITICAL_ADVERTISING` (which blocks serving in the EU) or `DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING` ([camp], [eups]).

- **Missing field:** "In earlier API versions [before v26] this field is required for all new campaigns". In v25 a create without it fails with `FieldError.REQUIRED`, through `GoogleAdsService.Mutate` and batch jobs alike ([eupar]).
- **Account-level block:** From 1 April 2026, if an account holds undeclared campaigns that are not exempt, campaign-management mutates fail with `MutateError.EU_POLITICAL_ADVERTISING_DECLARATION_REQUIRED`. A mutate that only sets this field still works and clears the block ([eupar], [mute]).
- **Criteria on undeclared campaigns:** campaign criteria fail with `CriterionError.MISSING_EU_POLITICAL_ADVERTISING_SELF_DECLARATION` ([eupar], [cre]).
- **v26 change:** the field becomes optional for campaigns that do not positively target the EU ([eupar]).
- **PPCWay:** sends `DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING` after the merchant confirms it (`builder/campaign.py`).

### 1.7 Request size and operation limits

| Limit | Value | Source |
|---|---|---|
| Mutate operations per request | 10,000 (20,000 if every operation is an `AdGroupCriterionOperation`). Over the limit: `RequestError.TOO_MANY_MUTATE_OPERATIONS` | [quotas], [mbp] |
| Action operations per Mutate | 100. Over the limit: `RequestError.TOO_MANY_ACTION_OPERATIONS` | [mbp] |
| Temporary names per request | No limit | [mut] |
| Message and response size | gRPC default 4 MB; client libraries raise it to 64 MB and "responses must not exceed this limit". REST request size limit **(unconfirmed)** | [quotas] |
| Daily operations, Test access | 15,000 per day, test accounts only | [quotas], [access] |
| Daily operations, Explorer access | 2,880 per day on production accounts, 15,000 on test accounts. Account creation, user management, planning and billing services are blocked | [quotas], [access] |
| Daily operations, Basic access | 15,000 per day on test and production accounts | [quotas], [access] |
| Daily operations, Standard access | Unlimited | [quotas], [access] |
| Daily cap error | `QuotaError.RESOURCE_EXHAUSTED` | [quotas] |
| What counts | Each mutate operation and each Search or SearchStream request. Requests rejected with a `GoogleAdsFailure` count; network failures do not. Validate-only **(unconfirmed)** | [quotas] |
| Rate limits | Token bucket on queries per second, enforced per customer id and per Cloud project, plus a cap on operations per minute. Error `QuotaError.RESOURCE_TEMPORARILY_EXHAUSTED`; `QuotaErrorDetails` gives `rate_scope`, `rate_name`, `retry_delay` | [rate], [qe], [qed] |
| Operations per batch job | 1,000,000 | [bbp] |
| Active or pending batch jobs per account | 100 | [bbp] |
| Operations per AddBatchJobOperations call | 10,000 hard limit (`BatchJobError.REQUEST_TOO_LARGE`); 1,000 recommended | [bbp], [mbp] |
| Batch request and operation size | 41,937,920 bytes per request; 10,484,504 bytes per operation | [bbp], [mbp] |
| Pending batch jobs | Removed automatically after 7 days. How long finished results are kept **(unconfirmed)** | [bbp] |
| ListBatchJobResults page size | At most 1,000 | [bbp], [bflow] |
| Campaigns per account | 10,000 active and paused | [help] |
| Ad groups per campaign | 20,000 | [help] |
| Ad group targeting items (keywords and others) | 20,000 per ad group; 5 million per account | [help] |
| Campaign targeting items (locations, campaign negatives) | 1 million per account | [help] |
| Location targets per campaign | 10,500 (10,000 locations plus 500 proximity) | [help] |
| Enabled responsive search ads per ad group | 3 | [help] |
| Active text and other non-image ads | 50 per ad group; 4 million per account | [help] |
| Responsive search ad text | 3 to 15 headlines, 2 to 4 descriptions; headline 30 characters, description 90, `path1` and `path2` 15 each, final URL 2,084 bytes | [rsa], [sys] |
| Keyword length | 80 characters | [sys] |
| Campaign name, ad group name | 256 characters each | [sys] |
| Negative keywords per campaign | 10,000 | [help] |
| Negative keyword lists (shared sets) | 20 per account, 5,000 keywords per list | [help] |
| Budgets per account | 11,000 shared; 20,000 not shared | [help], [sys] |
| Assets | 50,000 campaign-level per account; 250,000 ad group-level per account; 10,000 ad group-level per campaign | [help] |
| Account budget and billing services | 1 operation per mutate request | [quotas] |
| Limit breach error | `ResourceCountLimitExceededError.ACCOUNT_LIMIT`, `CAMPAIGN_LIMIT`, `ADGROUP_LIMIT`, `AD_GROUP_AD_LIMIT`, `SHARED_SET_LIMIT`, `RESOURCE_LIMIT`; `details.resource_count_details` gives `enclosing_id`, `enclosing_resource`, `existing_count`, `limit`, `limit_type` | [rcl], [rcd] |

### 1.8 Error handling for common creation failures

**Shape of a refusal.** A REST failure returns an HTTP status (400 for INVALID_ARGUMENT, 429 for RESOURCE_EXHAUSTED, 403 for PERMISSION_DENIED and so on) whose `error.details[]` holds a `GoogleAdsFailure` with `errors[]` and `request_id` ([uae], [gaf]). Each `GoogleAdsError` carries `error_code` (a oneof such as `campaign_budget_error: DUPLICATE_NAME`), `message`, `trigger` (the offending value), `location.field_path_elements[]` (each with `field_name` and `index`), and `details` (`policy_finding_details`, `policy_violation_details`, `quota_error_details`, `resource_count_details`, `budget_per_day_minimum_error_details` and others) ([gae], [ec], [eloc], [fpe], [ed]).

**Finding the failed operation.** `field_path_elements[0].index` is "the 0-based index of the operation in the original request" ([pf]). Google's examples show the field name `operations` for per-service mutates; for `GoogleAdsService.Mutate` it is the `mutate_operations` field, and its casing in REST JSON is **(unconfirmed)**. PPCWay's gateway already accepts both spellings.

**What to retry.** In atomic mode nothing is applied on failure, so a transient error can be retried whole. Google says to retry "only for transient server errors such as UNAVAILABLE, DEADLINE_EXCEEDED, INTERNAL, UNKNOWN, and ABORTED", with exponential backoff and jitter ([uae], [et]). If a timeout leaves no response, the create may or may not have landed, and a retry can then hit a `DUPLICATE_*` error; that last point is our inference, not Google's.

**What PPCWay does today.** `gateway/google.py` reports only the first error, maps its index to the operation, and does not retry on the create path, so only the first of several validation errors reaches the merchant.

| Error enum and value | When it happens at creation | Retry or fix | Source |
|---|---|---|---|
| `FieldError.REQUIRED`, `RequestError.REQUIRED_FIELD_MISSING` | A required field is missing, including `contains_eu_political_advertising` in v25 | Fix | [fe], [reqe], [eupar] |
| `MutateError.EU_POLITICAL_ADVERTISING_DECLARATION_REQUIRED` | The account holds undeclared campaigns (from 1 April 2026) | Fix: declare the old campaigns | [mute], [eupar] |
| `CampaignBudgetError.DUPLICATE_NAME` | Budget name already exists | Fix: unique name, or refresh local state | [cbe] |
| `CampaignError.DUPLICATE_CAMPAIGN_NAME`, `AdGroupError.DUPLICATE_ADGROUP_NAME`, `SharedSetError.DUPLICATE_NAME` | Name clash with an existing enabled or paused resource | Fix. Google calls these "sync-related": refresh, do not retry | [ce2], [age], [sse], [et] |
| `CampaignBudgetError.BUDGET_BELOW_PER_DAY_MINIMUM` | Budget under the per-day minimum. `details.budget_per_day_minimum_error_details` gives `budget_per_day_minimum_micros`, `minimum_budget_amount_micros`, `currency_code` | Fix | [cbe], [bpdm] |
| `CampaignBudgetError.MONEY_AMOUNT_LESS_THAN_CURRENCY_MINIMUM_CPC`, `NON_MULTIPLE_OF_MINIMUM_CURRENCY_UNIT`, `TOTAL_BUDGET_AMOUNT_MUST_BE_UNSET_FOR_BUDGET_PERIOD_DAILY` | Bad budget amount or unit | Fix | [cbe], [ce] |
| `CampaignError.CANNOT_SET_DATE_TO_PAST`, `DateRangeError.CANNOT_SET_DATE_TO_PAST`, `START_DATE_AFTER_END_DATE`, `AFTER_MAXIMUM_ALLOWABLE_DATE` | Start or end in the past or out of order | Fix | [ce2], [dre], [camp] |
| `CampaignError.CAMPAIGN_MUST_TARGET_AT_LEAST_ONE_NETWORK`, `CANNOT_TARGET_SEARCH_NETWORK_WITHOUT_GOOGLE_SEARCH`, `CANNOT_TARGET_CONTENT_NETWORK` | Bad network settings | Fix | [ce2] |
| `BiddingError.BIDDING_STRATEGY_NOT_AVAILABLE_FOR_ACCOUNT_TYPE`, `CANNOT_CREATE_CAMPAIGN_WITH_BIDDING_STRATEGY`, `BIDDING_STRATEGY_NOT_SUPPORTED_WITH_AD_SCHEDULE`, `BID_TOO_SMALL`, `BID_TOO_BIG`, `BID_TOO_MANY_FRACTIONAL_DIGITS` | Strategy not allowed at creation, or a bid out of range or precision | Fix | [be], [ce] |
| `AdGroupError.BID_TYPE_AND_BIDDING_STRATEGY_MISMATCH` | Ad group bid does not match the campaign strategy | Fix | [age] |
| `StringLengthError.TOO_LONG`, `TOO_SHORT`, `EMPTY` | A name or text over or under its limit | Fix | [sle] |
| `AdError.TOO_LONG`, `LINE_TOO_WIDE`, `CANNOT_SET_PATH2_WITHOUT_PATH1`, `URL_NO_SCHEME`, `URL_MALFORMED`, `INVALID_INPUT` | Responsive search ad text, path or URL problems | Fix | [ade], [ce] |
| `CollectionSizeError.TOO_FEW`, `TOO_MANY` | Likely when headline or description counts fall outside 3 to 15 or 2 to 4 **(unconfirmed which error fires)** | Fix | [cse] |
| `DistinctError.DUPLICATE_ELEMENT` | Identical repeated values, such as duplicate custom parameter keys | Fix | [ce] |
| `CriterionError.KEYWORD_TEXT_TOO_LONG`, `KEYWORD_HAS_TOO_MANY_WORDS`, `KEYWORD_HAS_INVALID_CHARS`, `AdGroupCriterionError.INVALID_KEYWORD_TEXT` | Bad keyword text | Fix | [cre], [agce] |
| `AssetError.DUPLICATE_ASSET`, `DUPLICATE_ASSET_NAME`, `CALL_INVALID_PHONE_NUMBER`, `CALL_PHONE_NUMBER_NOT_SUPPORTED_FOR_COUNTRY` | Asset duplicated in one request, or a bad call asset | Fix. For a duplicate, create once and reuse the temporary id | [ase], [ce] |
| `PolicyFindingError.POLICY_FINDING` | Ad text or URL hits a PROHIBITED topic | Fix, or resend with `ignorable_policy_topics` | [pfe], [pexads] |
| `PolicyViolationError.POLICY_ERROR` | A keyword violates a policy | Fix, or resend with `exempt_policy_violation_keys` if `is_exemptible` | [pve], [pvd] |
| `PolicyValidationParameterError.CANNOT_SET_BOTH_IGNORABLE_POLICY_TOPICS_AND_EXEMPT_POLICY_VIOLATION_KEYS`, `UNSUPPORTED_AD_TYPE_FOR_IGNORABLE_POLICY_TOPICS`, `UNSUPPORTED_AD_TYPE_FOR_EXEMPT_POLICY_VIOLATION_KEYS` | Exemption fields misused | Fix | [pvpe] |
| `NewResourceCreationError.DUPLICATE_TEMP_IDS`, `TEMP_ID_RESOURCE_HAD_ERRORS`, `CANNOT_SET_ID_FOR_CREATE` | Temporary id reused, parent failed, or id set on create | Fix (for a failed parent, fix the parent) | [nrc] |
| `MutateError.RESOURCE_NOT_FOUND`, `RequestError.RESOURCE_NAME_MALFORMED`, `BAD_RESOURCE_ID` | Reference to a missing or malformed resource, or a temporary id used before its create | Fix | [mute], [reqe], [ce] |
| `MutateError.ID_EXISTS_IN_MULTIPLE_MUTATES`, `RESOURCE_ALREADY_EXISTS` | Same resource touched twice, or it already exists | Fix | [mute] |
| `RequestError.TOO_MANY_MUTATE_OPERATIONS`, `DatabaseError.REQUEST_TOO_LARGE` | Request too big | Fix: split | [reqe], [dbe], [quotas] |
| `ResourceCountLimitExceededError.*` | An account, campaign, ad group or shared set limit is reached | Fix: remove or reuse | [rcl], [ce] |
| `RangeError.TOO_LOW`, `TOO_HIGH` | A number out of range (often an unset id that defaults to 0) | Fix | [rge], [ce] |
| `QuotaError.RESOURCE_TEMPORARILY_EXHAUSTED` | Rate limit (queries per second or operations per minute) | Retry after `quota_error_details.retry_delay`, with backoff | [qe], [rate], [qed] |
| `QuotaError.RESOURCE_EXHAUSTED` | Daily cap for the access level | Wait for the reset, or move to a higher access level | [qe], [quotas], [ce] |
| `AuthorizationError.USER_PERMISSION_DENIED`, `CUSTOMER_NOT_ENABLED`, `ACTION_NOT_PERMITTED_FOR_SUSPENDED_ACCOUNT`, `CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION` | Missing `login-customer-id`, account not enabled or suspended, or a test-only project used on production | Fix | [aze], [ce] |
| `AuthenticationError.CUSTOMER_NOT_FOUND` | Account created moments ago | Retry: wait about 5 minutes, then every 30 seconds | [ce] |
| `DatabaseError.CONCURRENT_MODIFICATION` | Two writes to the same campaign or account at once | Retry; avoid concurrent mutates on one campaign | [dbe], [mbp] |
| `InternalError.INTERNAL_ERROR`, `TRANSIENT_ERROR` | Server fault | Retry with exponential backoff | [ie], [ce], [et] |
| `InternalError.DEADLINE_EXCEEDED` | Large or slow request | Retry after about 30 seconds; split the request if it persists | [ie], [ce] |
| `CampaignError.AI_MAX_MUST_BE_ENABLED`, `CriterionError.AI_MAX_MUST_BE_ENABLED`, `ContextError.OPERATION_NOT_PERMITTED_FOR_CONTEXT` | AI Max controls sent without AI Max on, or URL expansion without text automation (section 2.5) | Fix | [ce2], [aimax] |
| `CampaignError.CANNOT_SET_CAMPAIGN_KEYWORD_MATCH_TYPE` | `campaign.keyword_match_type` set to `BROAD` (section 2.4) | Fix: drop the field | [ce2], [aimax] |
| `CampaignError.REQUIRED_BUSINESS_NAME_ASSET_NOT_LINKED`, `REQUIRED_LOGO_ASSET_NOT_LINKED` | Performance Max with brand guidelines on, but no business name or square logo linked as a campaign asset | Fix | [ce2] |

[req]: https://developers.google.com/google-ads/api/reference/rpc/v25/MutateGoogleAdsRequest
[resp]: https://developers.google.com/google-ads/api/reference/rpc/v25/MutateGoogleAdsResponse
[mut]: https://developers.google.com/google-ads/api/reference/rpc/v25/GoogleAdsService/Mutate
[mop]: https://developers.google.com/google-ads/api/reference/rpc/v25/MutateOperation
[mopr]: https://developers.google.com/google-ads/api/reference/rpc/v25/MutateOperationResponse
[rct]: https://developers.google.com/google-ads/api/reference/rpc/v25/ResponseContentTypeEnum.ResponseContentType
[restmut]: https://developers.google.com/google-ads/api/rest/common/mutate
[mbp]: https://developers.google.com/google-ads/api/docs/mutating/best-practices
[mov]: https://developers.google.com/google-ads/api/docs/mutating/overview
[bulk]: https://developers.google.com/google-ads/api/docs/mutating/bulk-mutate
[struct]: https://developers.google.com/google-ads/api/docs/concepts/api-structure
[test]: https://developers.google.com/google-ads/api/docs/best-practices/testing
[pf]: https://developers.google.com/google-ads/api/docs/best-practices/partial-failures
[tmp]: https://developers.google.com/google-ads/api/docs/batch-processing/temporary-ids
[bov]: https://developers.google.com/google-ads/api/docs/batch-processing/overview
[bbp]: https://developers.google.com/google-ads/api/docs/batch-processing/best-practices
[bflow]: https://developers.google.com/google-ads/api/docs/batch-processing/flow
[abjo]: https://developers.google.com/google-ads/api/reference/rpc/v25/AddBatchJobOperationsRequest
[bjm]: https://developers.google.com/google-ads/api/reference/rpc/v25/BatchJob.BatchJobMetadata
[pex]: https://developers.google.com/google-ads/api/docs/policy-exemption/overview
[pexads]: https://developers.google.com/google-ads/api/docs/policy-exemption/ads
[validad]: https://developers.google.com/google-ads/api/samples/validate-ad
[pvp]: https://developers.google.com/google-ads/api/reference/rpc/v25/PolicyValidationParameter
[pvpe]: https://developers.google.com/google-ads/api/reference/rpc/v25/PolicyValidationParameterErrorEnum.PolicyValidationParameterError
[agao]: https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupAdOperation
[agco]: https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupCriterionOperation
[pvk]: https://developers.google.com/google-ads/api/reference/rpc/v25/PolicyViolationKey
[pvd]: https://developers.google.com/google-ads/api/reference/rpc/v25/PolicyViolationDetails
[pfd]: https://developers.google.com/google-ads/api/reference/rpc/v25/PolicyFindingDetails
[pte]: https://developers.google.com/google-ads/api/reference/rpc/v25/PolicyTopicEntry
[ptet]: https://developers.google.com/google-ads/api/reference/rpc/v25/PolicyTopicEntryTypeEnum.PolicyTopicEntryType
[pfe]: https://developers.google.com/google-ads/api/reference/rpc/v25/PolicyFindingErrorEnum.PolicyFindingError
[pve]: https://developers.google.com/google-ads/api/reference/rpc/v25/PolicyViolationErrorEnum.PolicyViolationError
[agaps]: https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupAdPolicySummary
[pas]: https://developers.google.com/google-ads/api/reference/rpc/v25/PolicyApprovalStatusEnum.PolicyApprovalStatus
[prs]: https://developers.google.com/google-ads/api/reference/rpc/v25/PolicyReviewStatusEnum.PolicyReviewStatus
[agaf]: https://developers.google.com/google-ads/api/fields/v25/ad_group_ad
[agc]: https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupCriterion
[agcas]: https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupCriterionApprovalStatusEnum.AdGroupCriterionApprovalStatus
[camp]: https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign
[eups]: https://developers.google.com/google-ads/api/reference/rpc/v25/EuPoliticalAdvertisingStatusEnum.EuPoliticalAdvertisingStatus
[eupar]: https://developers.google.com/google-ads/api/docs/api-policy/eu-par
[quotas]: https://developers.google.com/google-ads/api/docs/best-practices/quotas
[access]: https://developers.google.com/google-ads/api/docs/api-policy/access-levels
[rate]: https://developers.google.com/google-ads/api/docs/best-practices/rate-limits
[sys]: https://developers.google.com/google-ads/api/docs/best-practices/system-limits
[help]: https://support.google.com/google-ads/answer/6372658
[rsa]: https://developers.google.com/google-ads/api/docs/responsive-search-ads/overview
[gaf]: https://developers.google.com/google-ads/api/reference/rpc/v25/GoogleAdsFailure
[gae]: https://developers.google.com/google-ads/api/reference/rpc/v25/GoogleAdsError
[ec]: https://developers.google.com/google-ads/api/reference/rpc/v25/ErrorCode
[eloc]: https://developers.google.com/google-ads/api/reference/rpc/v25/ErrorLocation
[fpe]: https://developers.google.com/google-ads/api/reference/rpc/v25/ErrorLocation.FieldPathElement
[ed]: https://developers.google.com/google-ads/api/reference/rpc/v25/ErrorDetails
[uae]: https://developers.google.com/google-ads/api/docs/best-practices/understand-api-errors
[et]: https://developers.google.com/google-ads/api/docs/best-practices/error-types
[ce]: https://developers.google.com/google-ads/api/docs/common-errors
[qed]: https://developers.google.com/google-ads/api/reference/rpc/v25/QuotaErrorDetails
[rcd]: https://developers.google.com/google-ads/api/reference/rpc/v25/ResourceCountDetails
[bpdm]: https://developers.google.com/google-ads/api/reference/rpc/v25/BudgetPerDayMinimumErrorDetails
[mute]: https://developers.google.com/google-ads/api/reference/rpc/v25/MutateErrorEnum.MutateError
[nrc]: https://developers.google.com/google-ads/api/reference/rpc/v25/NewResourceCreationErrorEnum.NewResourceCreationError
[reqe]: https://developers.google.com/google-ads/api/reference/rpc/v25/RequestErrorEnum.RequestError
[rcl]: https://developers.google.com/google-ads/api/reference/rpc/v25/ResourceCountLimitExceededErrorEnum.ResourceCountLimitExceededError
[cbe]: https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignBudgetErrorEnum.CampaignBudgetError
[ce2]: https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignErrorEnum.CampaignError
[dre]: https://developers.google.com/google-ads/api/reference/rpc/v25/DateRangeErrorEnum.DateRangeError
[be]: https://developers.google.com/google-ads/api/reference/rpc/v25/BiddingErrorEnum.BiddingError
[age]: https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupErrorEnum.AdGroupError
[ade]: https://developers.google.com/google-ads/api/reference/rpc/v25/AdErrorEnum.AdError
[agae]: https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupAdErrorEnum.AdGroupAdError
[ase]: https://developers.google.com/google-ads/api/reference/rpc/v25/AssetErrorEnum.AssetError
[cre]: https://developers.google.com/google-ads/api/reference/rpc/v25/CriterionErrorEnum.CriterionError
[agce]: https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupCriterionErrorEnum.AdGroupCriterionError
[sle]: https://developers.google.com/google-ads/api/reference/rpc/v25/StringLengthErrorEnum.StringLengthError
[rge]: https://developers.google.com/google-ads/api/reference/rpc/v25/RangeErrorEnum.RangeError
[fe]: https://developers.google.com/google-ads/api/reference/rpc/v25/FieldErrorEnum.FieldError
[cse]: https://developers.google.com/google-ads/api/reference/rpc/v25/CollectionSizeErrorEnum.CollectionSizeError
[sse]: https://developers.google.com/google-ads/api/reference/rpc/v25/SharedSetErrorEnum.SharedSetError
[dbe]: https://developers.google.com/google-ads/api/reference/rpc/v25/DatabaseErrorEnum.DatabaseError
[qe]: https://developers.google.com/google-ads/api/reference/rpc/v25/QuotaErrorEnum.QuotaError
[ie]: https://developers.google.com/google-ads/api/reference/rpc/v25/InternalErrorEnum.InternalError
[aze]: https://developers.google.com/google-ads/api/reference/rpc/v25/AuthorizationErrorEnum.AuthorizationError
[aimax]: https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns

## 2. Campaign-level settings

Every setting in this section lives on the `Campaign` resource (https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign) or on the `CampaignBudget` it points to, and is created by a `campaign_operation` or `campaign_budget_operation` inside the one `GoogleAdsService.Mutate` request. In REST JSON, field paths are written in lowerCamelCase (for example `advertisingChannelType`); this document uses the snake_case names from the reference.

### 2.1 Channel, status, dates and budget

v25 has no `start_date` or `end_date` on `Campaign`. The only date fields are `start_date_time` and `end_date_time`, both strings in the format `yyyy-MM-dd HH:mm:ss` in the account's time zone (https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign, https://developers.google.com/google-ads/api/docs/campaigns/create-campaigns). The create guide's prose gives that format, but its C#, Python and Ruby samples still use a compact `yyyyMMdd` style, so trust the reference and the guide's note, not the samples.

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Campaign type | `campaign.advertising_channel_type` | `SEARCH`, `PERFORMANCE_MAX`, and the others listed in section 9. Required at creation and immutable afterwards. | Campaign | All | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign | Yes, `SEARCH` |
| Campaign sub-type | `campaign.advertising_channel_sub_type` | Optional and immutable. It must be a valid sub-type of the channel type. Leave it unset for a standard Search or Performance Max campaign. The full enum is in section 9. | Campaign | All | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign | No |
| Name | `campaign.name` | String. Must be unique among the account's active and paused campaigns, or the request fails with `CampaignError.DUPLICATE_CAMPAIGN_NAME`. | Campaign | All | https://developers.google.com/google-ads/api/docs/campaigns/create-campaigns, https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignErrorEnum.CampaignError | Yes |
| Status | `campaign.status` | `ENABLED`, `PAUSED`, `REMOVED`. Defaults to `ENABLED` on create. Google's guide says to create a campaign `PAUSED` before its ads are attached; inside one atomic request the ads arrive together, so `ENABLED` is safe there. | Campaign | All | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignStatusEnum.CampaignStatus, https://developers.google.com/google-ads/api/docs/campaigns/create-campaigns | Yes, `ENABLED` |
| Start date and time | `campaign.start_date_time` | `yyyy-MM-dd HH:mm:ss`, account time zone. Use `00:00:00` for day granularity; time-of-day granularity only applies to some campaign types. Defaults to the current date. A date in the past fails with `CampaignError.CANNOT_SET_DATE_TO_PAST`. | Campaign | All | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign, https://developers.google.com/google-ads/api/docs/campaigns/create-campaigns, https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignErrorEnum.CampaignError | No |
| End date and time | `campaign.end_date_time` | Same format, `23:59:59` for day granularity. On create it defaults to running indefinitely. Required when the budget is a total (lifetime) budget, or the request fails with `CampaignError.END_DATE_TIME_REQUIRED_FOR_TOTAL_BUDGET`. | Campaign | All | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign, https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignErrorEnum.CampaignError | No |
| Budget link | `campaign.campaign_budget` | Resource name of a `CampaignBudget`, which can be a temporary name created earlier in the same request. | Campaign | All | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign | Yes |
| Daily budget | `campaign_budget.amount_micros` | int64 micros of the account currency, used when `period` is `DAILY`. Monthly spend is capped at 30.4 times this amount. Mutually exclusive with `total_amount_micros`. | Budget | All | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignBudget | Yes |
| Total (lifetime) budget | `campaign_budget.total_amount_micros` with `campaign_budget.period = CUSTOM_PERIOD` | int64 micros. Only used with `CUSTOM_PERIOD`. The campaign then needs an `end_date_time`. Performance Max requires a `DAILY` budget (section 6.1) and Demand Gen accepts a total budget (section 9); for SEARCH the v25 reference does not say **(unconfirmed)**. | Budget | DEMAND_GEN; not PERFORMANCE_MAX; SEARCH unconfirmed | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignBudget, https://developers.google.com/google-ads/api/reference/rpc/v25/BudgetPeriodEnum.BudgetPeriod, https://developers.google.com/google-ads/api/performance-max/getting-started, https://developers.google.com/google-ads/api/docs/demand-gen/create-campaign | No |
| Budget period | `campaign_budget.period` | `DAILY` (default), `CUSTOM_PERIOD`. Immutable. | Budget | All | https://developers.google.com/google-ads/api/reference/rpc/v25/BudgetPeriodEnum.BudgetPeriod | No (default `DAILY`) |
| Delivery method | `campaign_budget.delivery_method` | `STANDARD` (default). The v25 page names no other value in use. | Budget | All | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignBudget | Yes, `STANDARD` |
| Shared or not | `campaign_budget.explicitly_shared` | Defaults to **true** on create, so it must be sent as `false` for a single-campaign budget. A shared budget can never become non-shared. Performance Max needs a non-shared budget (see section 6). | Budget | All | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignBudget | Yes, `false` |
| Budget type | `campaign_budget.type` | `STANDARD` (default; a day may spend up to twice the daily amount), `FIXED_CPA` (Display only), `SMART_CAMPAIGN` (Smart only), `LOCAL_SERVICES` (Local Services only). Immutable. | Budget | See values | https://developers.google.com/google-ads/api/reference/rpc/v25/BudgetTypeEnum.BudgetType | No (default) |
| Budget name | `campaign_budget.name` | 1 to 255 UTF-8 bytes. Required for a shared budget. A name already used by another budget is refused (`DUPLICATE_NAME`, see section 1). | Budget | All | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignBudget | Yes |
| Budget aligned to a portfolio | `campaign_budget.aligned_bidding_strategy_id` | int64. Campaigns on this budget must then use that portfolio strategy. | Budget | Portfolio users | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignBudget | No |
| EU political advertising | `campaign.contains_eu_political_advertising` | `CONTAINS_EU_POLITICAL_ADVERTISING` (ads are then blocked from serving in the EU) or `DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING`. The create guide marks it required. The read-only `campaign.missing_eu_political_advertising_declaration` is true when a campaign lacks it. | Campaign | All | https://developers.google.com/google-ads/api/reference/rpc/v25/EuPoliticalAdvertisingStatusEnum.EuPoliticalAdvertisingStatus, https://developers.google.com/google-ads/api/docs/campaigns/create-campaigns | Yes, `DOES_NOT_CONTAIN...` |
| Payment mode | `campaign.payment_mode` | `PaymentMode` enum. Leave unset for Search and Performance Max **(enum values unconfirmed)**. | Campaign | Display (pay for conversions), Hotel | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign | No |

### 2.2 Bidding

A campaign carries exactly one member of the `campaign_bidding_strategy` oneof: either an embedded (standard) scheme or `bidding_strategy`, the resource name of a portfolio strategy (https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign). The v25 oneof members are `bidding_strategy`, `commission`, `fixed_cpm`, `manual_cpa`, `manual_cpc`, `manual_cpm`, `manual_cpv`, `maximize_conversion_value`, `maximize_conversions`, `percent_cpc`, `target_cpa`, `target_cpc`, `target_cpm`, `target_cpv`, `target_impression_share`, `target_roas` and `target_spend`. Google's strategy table says standalone `TARGET_CPA` and `TARGET_ROAS` are portfolio-only now; for a standard campaign, set a target inside `maximize_conversions` or `maximize_conversion_value` instead (https://developers.google.com/google-ads/api/docs/campaigns/bidding/strategy-types).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Maximize conversions | `campaign.maximize_conversions` (empty message is valid) | Sends bids for the most conversions within budget. | Campaign | Standard: SEARCH, DISPLAY, VIDEO, DEMAND_GEN, PERFORMANCE_MAX, MULTI_CHANNEL. Portfolio: SEARCH, SHOPPING, PERFORMANCE_MAX | https://developers.google.com/google-ads/api/reference/rpc/v25/MaximizeConversions, https://developers.google.com/google-ads/api/docs/campaigns/bidding/strategy-types | Yes, as `maximizeConversions: {}` for "leads" |
| Target CPA | `campaign.maximize_conversions.target_cpa_micros` | int64 micros. Optional. With it, bidding aims for the most conversions at or below this cost per conversion. | Campaign | SEARCH, PERFORMANCE_MAX and the others above | https://developers.google.com/google-ads/api/reference/rpc/v25/MaximizeConversions | No |
| Bid limits on maximize conversions | `campaign.maximize_conversions.cpc_bid_ceiling_micros`, `cpc_bid_floor_micros` | int64 micros. Mutable for portfolio strategies only, and ignored for Search campaigns. | Portfolio | Not SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/MaximizeConversions | No |
| Maximize conversion value | `campaign.maximize_conversion_value` | Bids for the most conversion value within budget. | Campaign | SEARCH, PERFORMANCE_MAX (section 6). Google's strategy table names no channel list for it **(other types unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/MaximizeConversionValue, https://developers.google.com/google-ads/api/docs/campaigns/bidding/strategy-types | No |
| Target ROAS | `campaign.maximize_conversion_value.target_roas` | double (3.5 means 350 percent). Optional. A high target may underspend. | Campaign | SEARCH, PERFORMANCE_MAX | https://developers.google.com/google-ads/api/reference/rpc/v25/MaximizeConversionValue | No |
| ROAS tolerance | `campaign.maximize_conversion_value.target_roas_tolerance_percent_millis` | int64 millis; 10,000 lets ROAS fall up to 10 percent below target for more volume. | Campaign | SEARCH, PERFORMANCE_MAX **(types unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/MaximizeConversionValue | No |
| Maximize clicks | `campaign.target_spend` (empty message is valid) | "as many clicks as possible within your budget". Optional `cpc_bid_ceiling_micros`. `target_spend_micros` is deprecated and "should no longer be used". | Campaign or portfolio | SEARCH. Not PERFORMANCE_MAX (section 6). The strategy table names no channel list **(other types unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/TargetSpend, https://developers.google.com/google-ads/api/docs/campaigns/bidding/strategy-types | Yes, as `targetSpend: {}` for "clicks" |
| Target impression share | `campaign.target_impression_share.location`, `.location_fraction_micros`, `.cpc_bid_ceiling_micros` | `location`: `ANYWHERE_ON_PAGE`, `TOP_OF_PAGE`, `ABSOLUTE_TOP_OF_PAGE`. `location_fraction_micros`: 1 percent is 10,000. `cpc_bid_ceiling_micros` is required. | Campaign or portfolio | SEARCH **(the API docs name no channel list; unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/TargetImpressionShare, https://developers.google.com/google-ads/api/reference/rpc/v25/TargetImpressionShareLocationEnum.TargetImpressionShareLocation | No |
| Manual CPC | `campaign.manual_cpc` with keyword or ad group bids in `cpc_bid_micros` | Manual bids per ad group or keyword. | Campaign | SEARCH and others **(the API docs name no channel list; unconfirmed)**. Standard only, not portfolio. | https://developers.google.com/google-ads/api/reference/rpc/v25/ManualCpc, https://developers.google.com/google-ads/api/docs/campaigns/bidding/strategy-types | No |
| Enhanced CPC | `campaign.manual_cpc.enhanced_cpc_enabled` | bool. Deprecated for Search and Display since the week of 31 March 2025: `true` has no effect and behaves as plain manual CPC. The field is still in v25 without a deprecation mark, and the `EnhancedCpc` portfolio scheme can no longer be created. Do not offer it. | Campaign | (deprecated) | https://developers.google.com/google-ads/api/docs/campaigns/bidding/strategy-types, https://developers.google.com/google-ads/api/reference/rpc/v25/EnhancedCpc, https://support.google.com/google-ads/answer/2464964 | No |
| Standalone target CPA or ROAS | `campaign.target_cpa`, `campaign.target_roas` | Portfolio-only per Google's table; use the targets inside maximize conversions or conversion value for a standard campaign. | Portfolio | SEARCH, SHOPPING, PERFORMANCE_MAX via portfolio | https://developers.google.com/google-ads/api/docs/campaigns/bidding/strategy-types | No |
| Portfolio strategy | `campaign.bidding_strategy` pointing at a `BiddingStrategy` created by `bidding_strategy_operation` | `bidding_strategy.name` (1 to 255 bytes, unique in the account) and one `scheme` member: `enhanced_cpc`, `maximize_conversion_value`, `maximize_conversions`, `target_cpa`, `target_impression_share`, `target_roas`, `target_spend`. Optional `aligned_campaign_budget_id`. `currency_code` is settable only in manager accounts. `type` and `status` are read-only. | Customer (shared) | SEARCH, SHOPPING, PERFORMANCE_MAX (maximize conversions and value) | https://developers.google.com/google-ads/api/reference/rpc/v25/BiddingStrategy | No |
| Other schemes | `manual_cpm`, `manual_cpv`, `target_cpm`, `target_cpv`, `fixed_cpm`, `percent_cpc`, `commission`, `manual_cpa`, `target_cpc` | `manual_cpa` is Local Services only, `target_cpc` is Demand Gen only, `commission` is no longer available, `manual_cpm` is Display Network only. None apply to Search or Performance Max. | Campaign | See values | https://developers.google.com/google-ads/api/docs/campaigns/bidding/strategy-types | No |

Performance Max accepts only maximize conversions or maximize conversion value, each with an optional target (see section 6).

### 2.3 Customer acquisition goal

v25 removed the old customer acquisition resources. `CustomerLifecycleGoal`, `CampaignLifecycleGoal`, `CampaignLifecycleGoalService.ConfigureCampaignLifecycleGoals` and `CustomerAcquisitionGoalSettings` are gone, and their v25 reference pages return 404 (https://developers.google.com/google-ads/api/docs/release-notes, https://developers.google.com/google-ads/api/reference/rpc/v24/CampaignLifecycleGoal). The replacement is the unified goals model: an account-level `Goal` with `new_customer_acquisition_goal_settings`, and a campaign-level `CampaignGoalConfig` with `campaign_new_customer_acquisition_settings.target_option` (`TARGET_ALL` or `TARGET_SPECIFIC`). Neither can go in `GoogleAdsService.Mutate`; they are sent through `GoalService.MutateGoals` and `CampaignGoalConfigService.MutateCampaignGoalConfigs` after the campaign exists (https://developers.google.com/google-ads/api/reference/rpc/v25/MutateOperation, https://developers.google.com/google-ads/api/docs/conversions/goals/lifecycle-goals). Full detail is in section 7.

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| New customer goal (account) | `goal.new_customer_acquisition_goal_settings.value_settings` via `GoalService.MutateGoals` | `additional_value`, `additional_high_lifetime_value`; one Goal per goal type | Account | **(unconfirmed in the API docs)** | https://developers.google.com/google-ads/api/reference/rpc/v25/Goal | No |
| New customer goal (campaign) | `campaign_goal_config.campaign_new_customer_acquisition_settings.target_option` via `CampaignGoalConfigService.MutateCampaignGoalConfigs` | `TARGET_ALL` (default; bid higher for new customers using the value settings), `TARGET_SPECIFIC` (new customers only) | Campaign | **(unconfirmed in the API docs)** | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignGoalConfig, https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignGoalSettings.CampaignNewCustomerAcquisitionGoalSettings | No |
| Old lifecycle goal | `campaign_lifecycle_goal.customer_acquisition_goal_settings` | Removed in v25; do not use | Not applicable | Not applicable | https://developers.google.com/google-ads/api/docs/release-notes | No |

### 2.4 Networks, locations, URLs, Dynamic Search Ads and match type

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Google Search | `campaign.network_settings.target_google_search` | bool | Campaign | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.NetworkSettings | Yes, `true` |
| Search partners | `campaign.network_settings.target_search_network` | bool. Requires `target_google_search` to be true. | Campaign | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.NetworkSettings | Yes, `false` |
| Display Network (Display Expansion on Search) | `campaign.network_settings.target_content_network` | bool | Campaign | SEARCH, DISPLAY | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.NetworkSettings, https://developers.google.com/google-ads/api/docs/campaigns/create-campaigns | Yes, `false` |
| Partner network | `campaign.network_settings.target_partner_search_network` | bool. Only for select partner accounts; leave false. It does not control Search Partners. | Campaign | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.NetworkSettings | Yes, `false` |
| YouTube | `campaign.network_settings.target_youtube` | bool | Campaign | VIDEO, DEMAND_GEN **(types unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.NetworkSettings | No |
| Google TV | `campaign.network_settings.target_google_tv_network` | bool | Campaign | VIDEO **(types unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.NetworkSettings | No |
| Location options (who sees the ad) | `campaign.geo_target_type_setting.positive_geo_target_type` | `PRESENCE` (people in or regularly in the place), `PRESENCE_OR_INTEREST` (in, or showing interest in), `SEARCH_INTEREST` (searching for the place; Search and standard Shopping only). | Campaign | SEARCH, PERFORMANCE_MAX and others | https://developers.google.com/google-ads/api/reference/rpc/v25/PositiveGeoTargetTypeEnum.PositiveGeoTargetType | Yes, `PRESENCE` |
| Location exclusion option | `campaign.geo_target_type_setting.negative_geo_target_type` | `PRESENCE`, `PRESENCE_OR_INTEREST` | Campaign | SEARCH, PERFORMANCE_MAX and others | https://developers.google.com/google-ads/api/reference/rpc/v25/NegativeGeoTargetTypeEnum.NegativeGeoTargetType | Yes, `PRESENCE` |
| Tracking template | `campaign.tracking_url_template` | String, may embed `{lpurl}` and custom parameters such as `{_promo}`. The lowest level that sets it wins. | Customer, campaign, ad group, ad, keyword | All | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign, https://developers.google.com/google-ads/api/docs/ads/upgraded-urls/fields | No |
| Final URL suffix | `campaign.final_url_suffix` | Query parameters appended to the landing page under parallel tracking. Lower levels override. | Customer, campaign, ad group, ad, keyword | All | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign, https://developers.google.com/google-ads/api/docs/ads/upgraded-urls/fields | No |
| Custom parameters | `campaign.url_custom_parameters[]` of `CustomParameter {key, value}` | Up to 8 per entity. Key at most 16 bytes, alphanumeric only; value at most 200 bytes. Keys are unique ignoring case, or `DistinctError.DUPLICATE_ELEMENT`. | Campaign, ad group, ad, keyword | All | https://developers.google.com/google-ads/api/reference/rpc/v25/CustomParameter, https://developers.google.com/google-ads/api/docs/ads/upgraded-urls/fields | No |
| Dynamic Search Ads | `campaign.dynamic_search_ads_setting.domain_name`, `.language_code`, `.use_supplied_urls_only` | `domain_name` and `language_code` are required when the setting is used. New Dynamic Search Ads ad groups (`SEARCH_DYNAMIC_ADS`) cannot be created from February 2027, and existing ones are upgraded to AI Max, so do not build on DSA (https://developers.google.com/ads/blog/posts/2026/08/migrate-campaign-level-broad-match-and). | Campaign | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.DynamicSearchAdsSetting | No |
| Campaign broad match | `campaign.keyword_match_type` | `BROAD` only. Deprecated: new settings have been blocked in every version since 3 August 2026 with `CampaignError.CANNOT_SET_CAMPAIGN_KEYWORD_MATCH_TYPE`, the field is removed from versions released after 1 September 2026, and existing broad match campaigns were moved to AI Max in September 2026. Use AI Max, or broad match on each keyword. The read-only `campaign.broad_match_migration_date_time` (new in v25) records when Google moved a broad match campaign to AI Max. | Campaign | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignKeywordMatchTypeEnum.CampaignKeywordMatchType, https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns, https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignErrorEnum.CampaignError, https://developers.google.com/ads/blog/posts/2026/08/migrate-campaign-level-broad-match-and | No |

Performance Max has no network or channel controls, so `network_settings` applies to Search (and the other channel types noted), not to Performance Max (https://developers.google.com/google-ads/api/docs/campaigns/overview).

### 2.5 AI Max for Search, final URL expansion, brand settings and text guidelines

AI Max for Search is switched on with one boolean, `campaign.ai_max_setting.enable_ai_max`, and its parts are then opted in through `campaign.asset_automation_settings` and ad group criteria (https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns). AI Max arrived in **v21** (released 6 August 2025) with `Campaign.ai_max_setting.enable_ai_max`, the output-only `bundling_required`, `AdGroup.ai_max_ad_group_setting.disable_search_term_matching`, `CampaignError.AI_MAX_MUST_BE_ENABLED`, ad group level brand lists, locations and URL rules, and the `FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION` automation type (https://developers.google.com/google-ads/api/docs/archived-release-notes). In v22, `Campaign.url_expansion_opt_out` was removed in favour of that automation type (same source). In August and September 2026 Google blocked new campaign-level broad match and legacy automatically created assets and moved existing ones to AI Max, which is why v25.1 added the read-only `aca_migration_date_time` and `broad_match_migration_date_time` (https://developers.google.com/ads/blog/posts/2026/08/migrate-campaign-level-broad-match-and, https://developers.google.com/google-ads/api/docs/release-notes). If PPCWay ever turns AI Max on, every keyword behaves as broad match until the ad group sets `disable_search_term_matching`, which would override the builder's phrase match.

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| AI Max on or off | `campaign.ai_max_setting.enable_ai_max` | bool. False or unset means no AI Max feature serves. Turning it on turns on search term matching by default. In Shopping, text customisation is always on with AI Max. | Campaign | SEARCH, SHOPPING | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.AiMaxSetting, https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns | No |
| AI Max required flag | `campaign.ai_max_setting.bundling_required` | Output only. True when the campaign has used AI Max before and must keep AI Max on to use text automation and brand list targeting. | Campaign | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.AiMaxSetting | No |
| Search term matching off for one ad group | `ad_group.ai_max_ad_group_setting.disable_search_term_matching` | bool. Keywords then keep their own match types. | Ad group | SEARCH with AI Max | https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns | No |
| Text customisation | `campaign.asset_automation_settings[]` with `asset_automation_type = TEXT_ASSET_AUTOMATION` and `asset_automation_status` | `OPTED_IN` or `OPTED_OUT`. Search default is opted out; Performance Max default is opted in. On Search, opting in needs AI Max on, or `CampaignError.AI_MAX_MUST_BE_ENABLED`. | Campaign | SEARCH, PERFORMANCE_MAX | https://developers.google.com/google-ads/api/reference/rpc/v25/AssetAutomationTypeEnum.AssetAutomationType, https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.AssetAutomationSetting, https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns | No |
| Final URL expansion | `campaign.asset_automation_settings[]` with `asset_automation_type = FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION` | `OPTED_IN` or `OPTED_OUT`. Search default off, Performance Max default on. On Search it needs AI Max on and `TEXT_ASSET_AUTOMATION` opted in, or `ContextError.OPERATION_NOT_PERMITTED_FOR_CONTEXT`. While URL expansion is in use, its text automation cannot be opted out. v25 has no `url_expansion_opt_out` field on `Campaign`. | Campaign | SEARCH, PERFORMANCE_MAX | https://developers.google.com/google-ads/api/reference/rpc/v25/AssetAutomationTypeEnum.AssetAutomationType, https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns, https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign | No |
| Other asset automation | `campaign.asset_automation_settings[]` with `GENERATE_ENHANCED_YOUTUBE_VIDEOS`, `GENERATE_IMAGE_ENHANCEMENT`, `GENERATE_IMAGE_EXTRACTION`, `GENERATE_LANDING_PAGE_PREVIEW`, `GENERATE_LANDING_PAGE_TEXT`, `GENERATE_SHORTER_YOUTUBE_VIDEOS`, `GENERATE_VERTICAL_YOUTUBE_VIDEOS`, `GENERATE_VIDEOS_FROM_OTHER_ASSETS`, `GENERATE_ANIMATED_IMAGES_FROM_OTHER_ASSETS`, `GENERATE_DESIGN_VERSIONS_FOR_IMAGES`, `AUTOMATED_VIDEO_CRAWL` | Each `OPTED_IN` or `OPTED_OUT`. Enhanced YouTube videos and image enhancement default on for Performance Max; image extraction follows the account's dynamic image setting; the rest default on for Demand Gen ad formats. | Campaign | PERFORMANCE_MAX, DEMAND_GEN | https://developers.google.com/google-ads/api/reference/rpc/v25/AssetAutomationTypeEnum.AssetAutomationType | No |
| Brand inclusions (AI Max) | `campaign_criterion.brand_list` or `ad_group_criterion.brand_list` with `negative = false`, pointing at a shared set of type `BRANDS` | Restricts matching to queries about listed brands. | Campaign or ad group | SEARCH with AI Max | https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns | No |
| Brand exclusions | `campaign_criterion.brand_list` with `negative = true` | Excludes queries about listed brands. | Campaign | SEARCH, PERFORMANCE_MAX | https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns | No |
| Location of interest (AI Max) | `ad_group_criterion.location` with `negative = false` | Needs AI Max on. Reported in `matched_location_interest_view`. | Ad group | SEARCH with AI Max | https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns | No |
| URL inclusions (AI Max page feed) | `ad_group_criterion.webpage` (`WebpageInfo`) with `negative = false`, plus a `PAGE_FEED` asset set linked by `CampaignAssetSet` | Up to three ANDed `conditions[]`; only `URL` and `CUSTOM_LABEL` operands. For `SEARCH_STANDARD` ad groups it needs AI Max on and `TEXT_ASSET_AUTOMATION` opted in, or `CriterionError.AI_MAX_MUST_BE_ENABLED`. | Ad group | SEARCH with AI Max | https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns | No |
| Text guidelines: excluded words | `campaign.text_guidelines.term_exclusions[]` | At most 25 entries, each at most 30 characters. Exact words or phrases kept out of generated text. | Campaign | SEARCH, PERFORMANCE_MAX (brand guidelines not needed) | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.TextGuidelines | No |
| Text guidelines: messaging restrictions | `campaign.text_guidelines.messaging_restrictions[]` of `{restriction_text, restriction_type}` | At most 40. `restriction_text` 1 to 300 characters; `restriction_type` must be `RESTRICTION_BASED_EXCLUSION`. | Campaign | SEARCH, PERFORMANCE_MAX | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.TextGuidelines, https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns | No |
| Brand guidelines switch | `campaign.brand_guidelines_enabled` | bool. Performance Max only. Immutable and writable only at creation; cannot be disabled later. An existing campaign can be switched on only through `CampaignService.EnablePMaxBrandGuidelines`. Not allowed for Travel Goals campaigns. When on, a business name and a square logo must be linked as campaign assets, or `CampaignError.REQUIRED_BUSINESS_NAME_ASSET_NOT_LINKED` / `REQUIRED_LOGO_ASSET_NOT_LINKED`. | Campaign | PERFORMANCE_MAX | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign, https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignService, https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignErrorEnum.CampaignError | No |
| Brand colours and font | `campaign.brand_guidelines.main_color`, `.accent_color`, `.predefined_font_family` | Hex colours such as `#00ff00`; if one colour is set, both are required. Font, case sensitive: `Open Sans`, `Roboto`, `Montserrat`, `Poppins`, `Lato`, `Oswald`, `Playfair Display`, `Roboto Slab`. Only with brand guidelines enabled. | Campaign | PERFORMANCE_MAX | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.BrandGuidelines, https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignErrorEnum.CampaignError | No |
| Brand exclusions and Shopping ads | `campaign.pmax_campaign_settings.brand_targeting_overrides.ignore_exclusions_for_shopping_ads` | bool. If true, brand exclusions do not apply to Shopping ads. | Campaign | PERFORMANCE_MAX | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.PmaxCampaignSettings.BrandTargetingOverrides | No |
| Block inherited assets | `campaign.excluded_parent_asset_field_types[]`, `campaign.excluded_parent_asset_set_types[]` | Asset field types not inherited from the account level; asset set types supports only `LOCATION_SYNC`. | Campaign | All with assets | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign | No |

### 2.6 Frequency caps, optimization goals, audience setting and targeting setting

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Frequency cap | `campaign.frequency_caps[]` of `FrequencyCapEntry {key, cap}`; `key` is `FrequencyCapKey {level, event_type, time_unit, time_length}` | `level`: `AD_GROUP_AD`, `AD_GROUP`, `CAMPAIGN`. `event_type`: `IMPRESSION`, `VIDEO_VIEW`. `time_unit`: `DAY`, `WEEK`, `MONTH`. `cap` is int32. At most one cap per key. | Campaign | DISPLAY, VIDEO, DEMAND_GEN **(types unconfirmed; the v25 reference does not list them)**. Not SEARCH or PERFORMANCE_MAX. | https://developers.google.com/google-ads/api/reference/rpc/v25/FrequencyCapEntry, https://developers.google.com/google-ads/api/reference/rpc/v25/FrequencyCapKey, https://developers.google.com/google-ads/api/reference/rpc/v25/FrequencyCapLevelEnum.FrequencyCapLevel, https://developers.google.com/google-ads/api/reference/rpc/v25/FrequencyCapEventTypeEnum.FrequencyCapEventType, https://developers.google.com/google-ads/api/reference/rpc/v25/FrequencyCapTimeUnitEnum.FrequencyCapTimeUnit | No |
| Optimization goals | `campaign.optimization_goal_setting.optimization_goal_types[]` | `CALL_CLICKS`, `DRIVING_DIRECTIONS`, `APP_PRE_REGISTRATION` | Campaign | `APP_PRE_REGISTRATION` is for App campaigns; which types take `CALL_CLICKS` and `DRIVING_DIRECTIONS` is not stated in the v25 reference **(unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.OptimizationGoalSetting, https://developers.google.com/google-ads/api/reference/rpc/v25/OptimizationGoalTypeEnum.OptimizationGoalType | No |
| Audience setting | `campaign.audience_setting.use_audience_grouped` | bool, immutable. True means the campaign targets through an `Audience` resource; false allows audience segment criteria. | Campaign | DEMAND_GEN, VIDEO **(types unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.AudienceSetting | No |
| Demand Gen upgraded targeting | `campaign.demand_gen_campaign_settings.upgraded_targeting` | bool, immutable, default true, settable only at creation. Lets location and language be set per ad group. | Campaign | DEMAND_GEN | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.DemandGenCampaignSettings | No |
| Targeting or observation | `campaign.targeting_setting.target_restrictions[]` (and `target_restriction_operations[]` on update) | Per targeting dimension, whether criteria narrow reach ("targeting") or only report and adjust bids ("observation"). Detail in section 3. | Campaign or ad group | SEARCH, DISPLAY and others | https://developers.google.com/google-ads/api/reference/rpc/v25/TargetingSetting | No |

## 3. Campaign criteria

> **Action for PPCWay now.** Since late September 2026, Google rejects any create or update of `campaign_criterion.language` on a Search campaign with `ContextError.OPERATION_NOT_PERMITTED_FOR_CONTEXT`. The change is not tied to an API version, so it applies on v25 too. Because PPCWay launches as one atomic request, that single language operation fails the whole launch. Google now matches language from the ad text, the landing page and the searcher's own settings. Existing language criteria can still be read and removed. Performance Max does not error, because language still applies to its channels outside Search. Sources: https://developers.google.com/google-ads/api/docs/deprecations, https://developers.google.com/google-ads/api/docs/targeting/criteria, https://developers.google.com/ads/blog/posts/2026/08/google-ads-language-targeting-changes

A criterion is set on a campaign (`CampaignCriterion`), on an ad group (`AdGroupCriterion`), or on the whole account (`CustomerNegativeCriterion`, exclusions only). Lists that several campaigns share are built from `SharedSet`, `SharedCriterion` and `CampaignSharedSet`; there is no ad group shared set link, and brand lists attach to an ad group through `AdGroupCriterion`. On both `CampaignCriterion` and `AdGroupCriterion`, the criterion field and `negative` are immutable, so a change is a remove plus a create (https://developers.google.com/google-ads/api/docs/targeting/overview, https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignCriterion, https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupCriterion).

**Criterion fields on `CampaignCriterion` in v25 (36):** `ad_schedule`, `age_range`, `brand_list`, `carrier`, `combined_audience`, `content_label`, `custom_affinity`, `custom_audience`, `device`, `extended_demographic`, `gender`, `income_range`, `ip_block`, `keyword`, `keyword_theme`, `language`, `life_event`, `listing_scope`, `local_service_id`, `location`, `location_group`, `mobile_app_category`, `mobile_application`, `mobile_device`, `operating_system_version`, `parental_status`, `placement`, `proximity`, `topic`, `user_interest`, `user_list`, `video_lineup`, `webpage`, `webpage_list` (not publicly available), `youtube_channel`, `youtube_video` (https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignCriterion).

**Criterion fields on `AdGroupCriterion` in v25 (30):** `age_range`, `app_payment_model`, `audience`, `brand_list`, `combined_audience`, `custom_affinity`, `custom_audience`, `custom_intent`, `entity_bid`, `extended_demographic`, `gender`, `income_range`, `keyword`, `language`, `life_event`, `listing_group`, `location`, `mobile_app_category`, `mobile_application`, `parental_status`, `placement`, `retail_filter_bundle`, `topic`, `user_interest`, `user_list`, `vertical_ads_item_group_rule_list`, `video_lineup`, `webpage`, `youtube_channel`, `youtube_video` (https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupCriterion).

**Which campaign types accept which criteria.** The API docs do not map most criteria to campaign types. Google's Performance Max page lists the campaign-level types it accepts: `AD_SCHEDULE`, `AGE_RANGE`, `BRAND`, `DEVICE`, `KEYWORD`, `LANGUAGE`, `LOCATION`, `LOCATION_GROUP` and `WEBPAGE`, with `BRAND` and `KEYWORD` as exclusions only (https://developers.google.com/google-ads/api/docs/performance-max/create-campaign-criteria). Where no source names a campaign type, the table says **(unconfirmed)**.

### 3.1 Common campaign criterion fields

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Status | `campaign_criterion.status` | `ENABLED`, `PAUSED`, `REMOVED` | Campaign | All | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignCriterionStatusEnum.CampaignCriterionStatus | No (default) |
| Negative | `campaign_criterion.negative` | bool, immutable; true excludes | Campaign | All | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignCriterion | Yes, on negative keywords |
| Bid modifier | `campaign_criterion.bid_modifier` | float 0.1 to 10.0; 0 opts out of a device | Campaign | See 3.3 | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignCriterion | No |
| Read-only fields | `criterion_id`, `display_name`, `type` | Output only | Campaign | All | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignCriterion | Not applicable |

### 3.2 Locations and language

Target a place with `location.geo_target_constant`, using an id from `GeoTargetConstantService.SuggestGeoTargetConstants` (section 8). Only a `LocationInfo` can be excluded; a radius (`ProximityInfo`) cannot. A location group draws a radius around location assets or around one geo target constant; feed ids are gone, though the legacy `feed_item_sets` field is still listed (https://developers.google.com/google-ads/api/docs/targeting/location-targeting, https://developers.google.com/google-ads/api/reference/rpc/v25/LocationGroupInfo).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Location | `campaign_criterion.location.geo_target_constant` | `geoTargetConstants/{id}` | Campaign, include and exclude. Ad group only for Demand Gen with upgraded targeting, and for AI Max "location of interest" (include, needs AI Max on) | All; listed for Performance Max | https://developers.google.com/google-ads/api/reference/rpc/v25/LocationInfo, https://developers.google.com/google-ads/api/docs/targeting/location-targeting, https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns/getting-started | Yes, include only |
| Excluded location | Same field with `negative = true` | `LocationInfo` only | Campaign | All | https://developers.google.com/google-ads/api/docs/targeting/location-targeting | No |
| Radius (proximity) | `campaign_criterion.proximity.geo_point.{latitude_in_micro_degrees, longitude_in_micro_degrees}`, `.radius` (double), `.radius_units`, `.address.{street_address, city_name, postal_code, country_code}` | `radius_units`: `KILOMETERS` (default), `MILES`. The address does not affect serving. Minimum and maximum radius not stated **(unconfirmed)** | Campaign, include only | SEARCH and others **(unconfirmed)**; not in the Performance Max list | https://developers.google.com/google-ads/api/reference/rpc/v25/ProximityInfo, https://developers.google.com/google-ads/api/reference/rpc/v25/ProximityRadiusUnitsEnum.ProximityRadiusUnits | No |
| Location group | `campaign_criterion.location_group.{geo_target_constants[] (at most 1), location_group_asset_sets[], enable_customer_level_location_asset_set, feed_item_sets[] (legacy), radius (int64, required), radius_units (required)}` | Units `METERS`, `MILES`, `MILLI_MILES`: `MILES` or `METERS` with a geo target constant, `MILLI_MILES` or `METERS` with asset sets. Asset set fields cannot be combined with `geo_target_constants` | Campaign, include only | Listed for Performance Max; SEARCH **(unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/LocationGroupInfo, https://developers.google.com/google-ads/api/reference/rpc/v25/LocationGroupRadiusUnitsEnum.LocationGroupRadiusUnits | No |
| Location matching | `campaign.geo_target_type_setting` (a campaign field, see 2.4) | Positive `PRESENCE`, `PRESENCE_OR_INTEREST`, `SEARCH_INTEREST`; negative `PRESENCE`, `PRESENCE_OR_INTEREST` | Campaign | As in 2.4 | https://developers.google.com/google-ads/api/reference/rpc/v25/PositiveGeoTargetTypeEnum.PositiveGeoTargetType | Yes, `PRESENCE` |
| Language | `campaign_criterion.language.language_constant`; `ad_group_criterion.language.language_constant` | `languageConstants/{id}`. Include only; languages cannot be excluded. A language Google does not allow returns `CriterionError.CANNOT_TARGET_LANGUAGE` (from v24.2) | Campaign (Display, Performance Max outside Search, App); ad group (Demand Gen) | **Not SEARCH**: rejected with `ContextError.OPERATION_NOT_PERMITTED_FOR_CONTEXT` since late September 2026 | https://developers.google.com/google-ads/api/reference/rpc/v25/LanguageInfo, https://developers.google.com/google-ads/api/docs/targeting/criteria, https://developers.google.com/google-ads/api/docs/deprecations | **Yes, on SEARCH. Remove it** |

### 3.3 Ad schedule, devices and bid modifiers

Each ad schedule entry is set once and cannot be updated: every field is required on create and prohibited on update, and a day holds at most six entries. A device, location or schedule adjustment goes in `campaign_criterion.bid_modifier`. `CampaignBidModifier` accepts only the calls interaction type. At ad group level, `AdGroupBidModifier` takes device and hotel dimensions. Smart Bidding (target CPA, target ROAS, maximize conversions, maximize conversion value) ignores manual adjustments, with two exceptions: device can be set to minus 100 percent under target impression share, target ROAS, maximize conversions and maximize conversion value, and under target CPA a device adjustment changes the target rather than the bid. Performance Max and Smart campaigns take no bid adjustments (https://developers.google.com/google-ads/api/docs/targeting/bid-modifiers, https://support.google.com/google-ads/answer/2732132).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Ad schedule | `campaign_criterion.ad_schedule.{day_of_week, start_hour, start_minute, end_hour, end_minute}` | `day_of_week` `MONDAY` to `SUNDAY`; `start_hour` 0 to 23; `end_hour` 0 to 24; minutes `ZERO`, `FIFTEEN`, `THIRTY`, `FORTY_FIVE`; the end minute is exclusive | Campaign, include only; `bid_modifier` allowed | SEARCH, DISPLAY, SHOPPING, VIDEO, DEMAND_GEN (Help); listed for Performance Max | https://developers.google.com/google-ads/api/reference/rpc/v25/AdScheduleInfo, https://developers.google.com/google-ads/api/reference/rpc/v25/DayOfWeekEnum.DayOfWeek, https://developers.google.com/google-ads/api/reference/rpc/v25/MinuteOfHourEnum.MinuteOfHour, https://support.google.com/google-ads/answer/2732132 | No |
| Device | `campaign_criterion.device.type` with `bid_modifier` | `MOBILE`, `TABLET`, `DESKTOP`, `CONNECTED_TV`, `OTHER` | Campaign, include only | SEARCH, DISPLAY, SHOPPING, VIDEO, DEMAND_GEN; Performance Max lists `DEVICE` | https://developers.google.com/google-ads/api/reference/rpc/v25/DeviceInfo, https://developers.google.com/google-ads/api/reference/rpc/v25/DeviceEnum.Device, https://developers.google.com/google-ads/api/docs/targeting/criteria | No |
| Ad group device modifier | `ad_group_bid_modifier.device.type`, `.bid_modifier` | 0.1 to 10.0; 0 opts out. Other members are hotel dimensions | Ad group | SEARCH, DISPLAY, SHOPPING, VIDEO, DEMAND_GEN | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupBidModifier | No |
| Call modifier | `campaign_bid_modifier.interaction_type.type`, `.bid_modifier` | `CALLS` only | Campaign | SEARCH only | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignBidModifier, https://developers.google.com/google-ads/api/reference/rpc/v25/InteractionTypeEnum.InteractionType, https://developers.google.com/google-ads/api/docs/targeting/bid-modifiers | No |
| Modifier ranges | `bid_modifier` as a multiplier (1.2 means plus 20 percent) | Device minus 100 to plus 900 percent; location, schedule, audience, demographics and calls minus 90 to plus 900 percent. Several modifiers multiply together | Campaign, ad group | Manual CPC and maximize clicks; none on Performance Max | https://support.google.com/google-ads/answer/2732132, https://developers.google.com/google-ads/api/docs/targeting/bid-modifiers | No |

### 3.4 IP exclusions, negative keywords and shared lists

An IP address can only be excluded, one criterion per address or CIDR block. Keywords at campaign level are exclusions only. An account can hold up to 20 shared negative keyword lists, plus one `ACCOUNT_LEVEL_NEGATIVE_KEYWORDS` list attached through `CustomerNegativeCriterion`. The API guide lists Search, Display, Shopping, App (`MULTI_CHANNEL`) and Local campaigns for shared negative keyword lists; Google Help says a shared list can now be picked for Performance Max in the UI, but API support for that is **(unconfirmed)** (https://developers.google.com/google-ads/api/docs/targeting/shared-sets, https://support.google.com/google-ads/answer/15726455).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| IP exclusion | `campaign_criterion.ip_block.ip_address`; `customer_negative_criterion.ip_block.ip_address` | IPv4 or IPv6, single address or CIDR block | Campaign or account; exclude only | Not stated **(unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/IpBlockInfo, https://developers.google.com/google-ads/api/reference/rpc/v25/CustomerNegativeCriterion | No |
| Campaign negative keyword | `campaign_criterion.keyword.{text, match_type}` with `negative = true` | `BROAD`, `PHRASE`, `EXACT` | Campaign, exclude only | SEARCH; PERFORMANCE_MAX (`KEYWORD`, exclude only, applies to Search and Shopping inventory; added in v20) | https://developers.google.com/google-ads/api/reference/rpc/v25/KeywordInfo, https://developers.google.com/google-ads/api/reference/rpc/v25/KeywordMatchTypeEnum.KeywordMatchType, https://developers.google.com/google-ads/api/docs/performance-max/create-campaign-criteria | Yes, `PHRASE` only |
| Ad group negative keyword | `ad_group_criterion.keyword` with `negative = true` | `BROAD`, `PHRASE`, `EXACT` | Ad group | SEARCH | https://developers.google.com/google-ads/api/docs/targeting/criteria | No (Otto adds exact-match ones after launch) |
| Negative keyword list | `shared_set.{name, type = NEGATIVE_KEYWORDS}`; `shared_criterion.{shared_set, keyword}`; `campaign_shared_set.{campaign, shared_set}` | Name 1 to 255 bytes, unique per type | Campaign (the link) | SEARCH, DISPLAY, SHOPPING, MULTI_CHANNEL, LOCAL in the API; Performance Max in the UI only per Help | https://developers.google.com/google-ads/api/docs/targeting/shared-sets, https://developers.google.com/google-ads/api/reference/rpc/v25/SharedSet, https://developers.google.com/google-ads/api/reference/rpc/v25/SharedCriterion, https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignSharedSet | No (the gateway can send shared sets, nothing does yet) |
| Account negative keywords | `shared_set.type = ACCOUNT_LEVEL_NEGATIVE_KEYWORDS` plus `customer_negative_criterion.negative_keyword_list.shared_set` | One list per account, 1,000 keywords | Account | Search and Shopping inventory, including Performance Max | https://developers.google.com/google-ads/api/docs/targeting/shared-sets, https://support.google.com/google-ads/answer/11396330 | No |
| Shared set types | `shared_set.type` | `NEGATIVE_KEYWORDS`, `ACCOUNT_LEVEL_NEGATIVE_KEYWORDS`, `NEGATIVE_PLACEMENTS`, `BRANDS`, `RETAIL_FILTER`, `VERTICAL_ADS_ITEM_GROUP_RULE_LIST`, `WEBPAGES` (not public) | Not applicable | Not applicable | https://developers.google.com/google-ads/api/reference/rpc/v25/SharedSetTypeEnum.SharedSetType | Not applicable |
| Shared criterion members | `shared_criterion.{brand, keyword, mobile_app_category, mobile_application, placement, retail_filter, vertical_ads_item_group_rule, webpage, youtube_channel, youtube_video}` | One per shared criterion | Shared set | Not applicable | https://developers.google.com/google-ads/api/reference/rpc/v25/SharedCriterion | Not applicable |

### 3.5 Audiences, targeting or observation, and demographics

Search, Display, Video, Hotel and standard Shopping campaigns take audience segments directly, at campaign or ad group level. `AudienceInfo` is a separate thing: an ad-group-only criterion for Demand Gen and App campaigns whose ad group sets `audience_setting.use_audience_grouped = true` at creation. Performance Max takes audiences only as asset group signals (section 6). `TargetingSetting` decides whether a dimension narrows who sees the ad ("targeting") or only reports and allows bid changes ("observation", `bid_only = true`); it can be set on the campaign or the ad group, never both. If `AUDIENCE` is left out it defaults to targeting, so a Search campaign that adds audiences for reporting must set `bid_only = true`. Demographic dimensions always run as observation; narrow them with exclusions (https://developers.google.com/google-ads/api/docs/targeting/targeting-settings, https://developers.google.com/google-ads/api/docs/remarketing/audiences).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| User list (remarketing, Customer Match) | `campaign_criterion.user_list.user_list`, `ad_group_criterion.user_list.user_list` | `UserList` resource name | Campaign and ad group; include and exclude | SEARCH, DISPLAY, VIDEO, HOTEL, SHOPPING | https://developers.google.com/google-ads/api/reference/rpc/v25/UserListInfo, https://developers.google.com/google-ads/api/docs/remarketing/audience-segments/getting-started | No |
| Interest (affinity, in-market) | `.user_interest.user_interest_category` | `UserInterest` resource name | Both; include and exclude | Varies by type, see guide | https://developers.google.com/google-ads/api/reference/rpc/v25/UserInterestInfo, https://developers.google.com/google-ads/api/docs/targeting/criteria | No |
| Custom audience | `.custom_audience.custom_audience` | `CustomAudience` resource name | Both; include only | SEARCH **(unconfirmed)**, DISPLAY, VIDEO | https://developers.google.com/google-ads/api/reference/rpc/v25/CustomAudienceInfo | No |
| Combined audience | `.combined_audience.combined_audience` | `CombinedAudience` resource name | Both; include only | **(unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/CombinedAudienceInfo | No |
| Custom affinity, custom intent | `.custom_affinity` (campaign or ad group), `.custom_intent` (ad group only) | Legacy `CustomInterest` | Include only | **(unconfirmed)** | https://developers.google.com/google-ads/api/docs/targeting/criteria | No |
| Audience | `ad_group_criterion.audience.audience` | `Audience` resource name; exclusions use user list segments only | Ad group, include only | DEMAND_GEN, MULTI_CHANNEL; Performance Max through asset group signals | https://developers.google.com/google-ads/api/docs/remarketing/audiences | No |
| Targeting or observation | `campaign.targeting_setting.target_restrictions[].{targeting_dimension, bid_only}` or `ad_group.targeting_setting` | Dimensions `AUDIENCE`, `TOPIC`, `GENDER`, `AGE_RANGE`, `PLACEMENT`, `PARENTAL_STATUS`, `INCOME_RANGE`, `KEYWORD` (`KEYWORD` cannot be `bid_only`) | Campaign or ad group, not both | SEARCH, SHOPPING, DISPLAY | https://developers.google.com/google-ads/api/docs/targeting/targeting-settings, https://developers.google.com/google-ads/api/reference/rpc/v25/TargetingDimensionEnum.TargetingDimension | No |
| Age | `.age_range.type` | `AGE_RANGE_18_24`, `AGE_RANGE_25_34`, `AGE_RANGE_35_44`, `AGE_RANGE_45_54`, `AGE_RANGE_55_64`, `AGE_RANGE_65_UP`, `AGE_RANGE_UNDETERMINED` | Campaign and ad group; include and exclude | SEARCH, DISPLAY, VIDEO; Performance Max lists `AGE_RANGE` | https://developers.google.com/google-ads/api/reference/rpc/v25/AgeRangeTypeEnum.AgeRangeType, https://developers.google.com/google-ads/api/docs/performance-max/create-campaign-criteria | No |
| Gender | `.gender.type` | `MALE`, `FEMALE`, `UNDETERMINED` | Both; include and exclude | SEARCH, DISPLAY, VIDEO; Performance Max campaign exclusions from v24 | https://developers.google.com/google-ads/api/reference/rpc/v25/GenderTypeEnum.GenderType, https://developers.google.com/google-ads/api/docs/release-notes | No |
| Household income | `.income_range.type` | `INCOME_RANGE_0_50`, `INCOME_RANGE_50_60`, `INCOME_RANGE_60_70`, `INCOME_RANGE_70_80`, `INCOME_RANGE_80_90`, `INCOME_RANGE_90_UP`, `INCOME_RANGE_UNDETERMINED` | Both; include and exclude | SEARCH, DISPLAY, VIDEO; Performance Max exclusions only from v26.2, not in v25 | https://developers.google.com/google-ads/api/reference/rpc/v25/IncomeRangeTypeEnum.IncomeRangeType, https://developers.google.com/google-ads/api/docs/release-notes | No |
| Parental status | `.parental_status.type` | `PARENT`, `NOT_A_PARENT`, `UNDETERMINED` | Campaign exclude only; ad group include and exclude | **(unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/ParentalStatusTypeEnum.ParentalStatusType, https://developers.google.com/google-ads/api/docs/targeting/criteria | No |
| Demographic rules | Not applicable | Excluding every value fails with `CANNOT_EXCLUDE_ALL_TARGETS` (from v24); leaving only `UNDETERMINED` fails with `CANNOT_TARGET_ONLY_UNDETERMINED` | Both | All | https://developers.google.com/google-ads/api/docs/targeting/criteria | Not applicable |
| Extended demographic, life event | `.extended_demographic`, `.life_event` | Inner fields not checked **(unconfirmed)** | Both; include and exclude | **(unconfirmed)** | https://developers.google.com/google-ads/api/docs/targeting/criteria | No |

### 3.6 Content labels, placements, brand lists, webpages and other criteria

Content labels are exclusions only, on the campaign or the account. Placement exclusions work on Display, Video and Demand Gen; for Performance Max, only account-level placement exclusions apply. A brand list is a `BRANDS` shared set: on Search it needs AI Max on (include at campaign or ad group level, exclude at campaign level), and Performance Max uses it for exclusions only.

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Content label | `campaign_criterion.content_label.type`; `customer_negative_criterion.content_label.type` | `BELOW_THE_FOLD`, `EMBEDDED_VIDEO`, `JUVENILE`, `LIVE_STREAMING_VIDEO`, `PARKED_DOMAIN`, `PROFANITY`, `SEXUALLY_SUGGESTIVE`, `SOCIAL_ISSUES`, `TRAGEDY`, `VIDEO`, `VIDEO_NOT_YET_RATED`, `VIDEO_RATING_DV_G`, `VIDEO_RATING_DV_PG`, `VIDEO_RATING_DV_T`, `VIDEO_RATING_DV_MA`, and the `BRAND_SUITABILITY_*` values (content for families, games fighting, games mature, health sensitive, health source undetermined, news recent, news sensitive, news source not featured, politics, religion) | Campaign or account; exclude only | DISPLAY, VIDEO, DEMAND_GEN; Performance Max at account level **(unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/ContentLabelInfo, https://developers.google.com/google-ads/api/reference/rpc/v25/ContentLabelTypeEnum.ContentLabelType | No |
| Placement | `.placement.url` | URL at most 250 characters | Campaign and ad group, include and exclude; account exclude | DISPLAY, VIDEO, DEMAND_GEN **(unconfirmed)**; Performance Max account level only | https://developers.google.com/google-ads/api/reference/rpc/v25/PlacementInfo, https://developers.google.com/google-ads/api/docs/targeting/criteria | No |
| YouTube video or channel | `.youtube_video.video_id`, `.youtube_channel.channel_id` | Ids | Campaign, ad group, account (exclude) | VIDEO, DEMAND_GEN **(unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/YouTubeVideoInfo, https://developers.google.com/google-ads/api/reference/rpc/v25/YouTubeChannelInfo | No |
| Mobile app category or app | `.mobile_app_category.mobile_app_category_constant`; `.mobile_application.{app_id, name}` (`app_id` starts `1-` for iOS, `2-` for Android) | Not applicable | Campaign, ad group, account (exclude) | DISPLAY, VIDEO **(unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/MobileAppCategoryInfo, https://developers.google.com/google-ads/api/reference/rpc/v25/MobileApplicationInfo | No |
| Negative placement list | `shared_set.type = NEGATIVE_PLACEMENTS` with `campaign_shared_set`, or `customer_negative_criterion.placement_list.shared_set` | Not applicable | Campaign or account | DISPLAY; Performance Max at account level | https://developers.google.com/google-ads/api/docs/targeting/shared-sets, https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignSharedSet | No |
| Brand list | `campaign_criterion.brand_list.shared_set`, `ad_group_criterion.brand_list.shared_set`; brands in `shared_criterion.brand` | `shared_set.type = BRANDS`; brand ids from `BrandSuggestionService` (section 8) | Campaign include and exclude; ad group include only, and an ad group list overrides the campaign list | SEARCH with AI Max on; PERFORMANCE_MAX exclude (`BRAND`); Shopping can ignore exclusions (`ignore_brand_exclusion_in_shopping_ads`, v24.2) | https://developers.google.com/google-ads/api/reference/rpc/v25/BrandListInfo, https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns/getting-started, https://developers.google.com/google-ads/api/docs/performance-max/create-campaign-criteria | No |
| Webpage | `.webpage.{criterion_name (required on create), conditions[] (ANDed)}`; `coverage_percentage` and `sample` are read only | In `SEARCH_STANDARD` ad groups only the `URL` and `CUSTOM_LABEL` operands; `URL` with `EQUALS` needs a full URL and must be the only condition | Campaign and ad group. A `SEARCH_STANDARD` ad group allows include only and needs AI Max with `TEXT_ASSET_AUTOMATION` on, plus a linked `PAGE_FEED` asset set | DSA (`SEARCH_DYNAMIC_ADS`); AI Max URL inclusions; Performance Max exclusions stop final URL expansion to those pages | https://developers.google.com/google-ads/api/reference/rpc/v25/WebpageInfo, https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns/getting-started, https://developers.google.com/google-ads/api/docs/performance-max/create-campaign-criteria | No |
| Keyword theme | `campaign_criterion.keyword_theme.{keyword_theme_constant or free_form_keyword_theme}` | Not applicable | Campaign | SMART only; no new Smart campaigns since 23 September 2026 | https://developers.google.com/google-ads/api/reference/rpc/v25/KeywordThemeInfo, https://developers.google.com/google-ads/api/docs/deprecations | No |
| Local service id | `campaign_criterion.local_service_id.service_id` | Not applicable | Campaign, include only | LOCAL_SERVICES | https://developers.google.com/google-ads/api/reference/rpc/v25/LocalServiceIdInfo | No |
| Other campaign-only criteria | `carrier`, `mobile_device`, `operating_system_version`, `listing_scope` | Include only | Campaign | DISPLAY, VIDEO, SHOPPING **(unconfirmed)** | https://developers.google.com/google-ads/api/docs/targeting/criteria | No |
| Topic, video lineup | `.topic`, `.video_lineup` | Include and exclude | Both | DISPLAY, VIDEO **(unconfirmed)** | https://developers.google.com/google-ads/api/docs/targeting/criteria | No |

### 3.7 Criteria limits

| Limit | Value | Source |
|---|---|---|
| Bid modifier range | 0.1 to 10.0; 0 opts out of a device | https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignCriterion, https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupBidModifier |
| Ad schedule entries per day | 6 | https://developers.google.com/google-ads/api/reference/rpc/v25/AdScheduleInfo |
| IP exclusions | 500 per campaign; 500 per account | https://developers.google.com/google-ads/api/reference/rpc/v25/IpBlockInfo, https://developers.google.com/google-ads/api/reference/rpc/v25/CustomerNegativeCriterion |
| Location targets per campaign | 10,500 in total, included and excluded: up to 10,000 places and 500 radius targets | https://support.google.com/google-ads/answer/6372658 |
| Geo target constants in a location group | 1 | https://developers.google.com/google-ads/api/reference/rpc/v25/LocationGroupInfo |
| Negative keywords per campaign | 10,000 (Performance Max also 10,000) | https://support.google.com/google-ads/answer/6372658, https://developers.google.com/google-ads/api/docs/performance-max/create-campaign-criteria |
| Campaign targeting items per account | 1,000,000 | https://support.google.com/google-ads/answer/6372658 |
| Shared negative keyword lists | 20 per account; 5,000 keywords per list | https://developers.google.com/google-ads/api/docs/targeting/shared-sets |
| Account-level negative keywords | 1 list per account, 1,000 keywords | https://developers.google.com/google-ads/api/docs/targeting/shared-sets, https://support.google.com/google-ads/answer/11396330 |
| Placement exclusion lists | 20 shared lists per account, 65,000 placements each; 65,000 account-level placement exclusions | https://support.google.com/google-ads/answer/6372658 |
| Brand lists | 10,000 per account, 10 per campaign, 5,000 brands per list | https://support.google.com/google-ads/answer/6372658 |
| Keyword text | 80 characters, 255 UTF-8 bytes, 10 words | https://developers.google.com/google-ads/api/docs/targeting/criteria |
| Placement URL | 250 characters | https://developers.google.com/google-ads/api/docs/targeting/criteria |
| Webpage conditions (AI Max) | 3 per criterion | https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns/getting-started |
| Shared set name | 1 to 255 UTF-8 bytes, unique per type | https://developers.google.com/google-ads/api/reference/rpc/v25/SharedSet |

## 4. Ad groups and ads

### 4.1 Ad group

On create, `name` is the only field marked required; `campaign` and `type` cannot be changed later. `cpc_bid_micros` is used only with manual CPC and is ignored under portfolio strategies. `target_cpa_micros` and `target_roas` override the campaign target only under the matching standard strategy. Performance Max has asset groups, not ad groups (https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroup).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Name | `ad_group.name` | Not empty, under 255 full-width UTF-8 characters, no null, line feed or carriage return | Ad group | All with ad groups | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroup | Yes |
| Campaign | `ad_group.campaign` | Immutable | Ad group | All | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroup | Yes |
| Status | `ad_group.status` | `ENABLED`, `PAUSED`, `REMOVED` | Ad group | All | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupStatusEnum.AdGroupStatus | Yes, `ENABLED` |
| Type | `ad_group.type` (immutable) | `SEARCH_STANDARD` (Search), `SEARCH_DYNAMIC_ADS` (DSA; no new ones from February 2027), `DISPLAY_STANDARD`, `SHOPPING_PRODUCT_ADS`, `SHOPPING_COMPARISON_LISTING_ADS`, `SHOPPING_SMART_ADS` (cannot be created), `HOTEL_ADS`, `PROMOTED_HOTEL_ADS`, `TRAVEL_ADS`, `SMART_CAMPAIGN_ADS`, `VIDEO_BUMPER`, `VIDEO_EFFICIENT_REACH`, `VIDEO_NON_SKIPPABLE_IN_STREAM`, `VIDEO_RESPONSIVE`, `VIDEO_TRUE_VIEW_IN_DISPLAY`, `VIDEO_TRUE_VIEW_IN_STREAM`, `YOUTUBE_AUDIO`. Demand Gen and App ad groups leave `type` unset | Ad group | As named | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupTypeEnum.AdGroupType, https://developers.google.com/google-ads/api/docs/demand-gen/create-campaign | Yes, `SEARCH_STANDARD` |
| Bids | `ad_group.cpc_bid_micros`, `cpm_bid_micros`, `cpv_bid_micros`, `percent_cpc_bid_micros`, `fixed_cpm_micros` | Micros | Ad group | CPC for Search manual CPC | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroup | No |
| Target overrides | `ad_group.target_cpa_micros`, `target_cpc_micros`, `target_cpm_micros`, `target_cpv_micros`, `target_roas` | Micros, or double for ROAS; `target_roas` errors under portfolio strategies | Ad group | SEARCH and others | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroup | No |
| Effective values | `effective_cpc_bid_micros`, `effective_target_cpa_micros` and `_source`, `effective_target_roas` and `_source` | Output only | Ad group | All | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroup | Not applicable |
| Ad rotation | `ad_group.ad_rotation_mode` | `OPTIMIZE`, `ROTATE_FOREVER` | Ad group | SEARCH, DISPLAY | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupAdRotationModeEnum.AdGroupAdRotationMode | No |
| URL options | `ad_group.tracking_url_template`, `final_url_suffix`, `url_custom_parameters[]` | As in 2.4 | Ad group | All | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroup | No |
| Targeting setting | `ad_group.targeting_setting.target_restrictions[]` | As in 3.5 | Ad group | SEARCH, DISPLAY | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroup | No |
| Audience setting | `ad_group.audience_setting.use_audience_grouped` (immutable) | bool | Ad group | DEMAND_GEN, MULTI_CHANNEL | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroup, https://developers.google.com/google-ads/api/docs/remarketing/audiences | No |
| Optimized targeting | `ad_group.optimized_targeting_enabled`, `exclude_demographic_expansion` | bool | Ad group | DISPLAY, DEMAND_GEN **(unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroup | No |
| AI Max ad group | `ad_group.ai_max_ad_group_setting.disable_search_term_matching` | bool | Ad group | SEARCH with AI Max | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroup, https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns/getting-started | No |
| Other settings | `demand_gen_ad_group_settings`, `video_ad_group_settings`, `vertical_ads_format_setting`, `display_custom_bid_dimension`, `excluded_parent_asset_field_types[]`, `excluded_parent_asset_set_types[]` (`LOCATION_SYNC` only) | Not applicable | Ad group | DEMAND_GEN, VIDEO, SEARCH (travel), DISPLAY | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroup | No |

### 4.2 Keywords

A keyword is an `AdGroupCriterion` with `keyword.text` and `keyword.match_type`. It can be an inclusion or an exclusion at ad group level, and only an exclusion at campaign level (3.4). Under AI Max, every keyword behaves as broad match unless the ad group turns search term matching off.

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Keyword | `ad_group_criterion.keyword.{text, match_type}` | `BROAD`, `PHRASE`, `EXACT`. Text at most 80 characters, 255 bytes, 10 words | Ad group | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/KeywordInfo, https://developers.google.com/google-ads/api/reference/rpc/v25/KeywordMatchTypeEnum.KeywordMatchType | Yes, `PHRASE` |
| Negative | `ad_group_criterion.negative` | bool, immutable | Ad group | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupCriterion | No |
| Status | `ad_group_criterion.status` | `ENABLED`, `PAUSED` (`REMOVED` is the deleted state) | Ad group | All | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupCriterionStatusEnum.AdGroupCriterionStatus | Yes, `ENABLED` |
| Keyword bid | `ad_group_criterion.cpc_bid_micros` (also `cpm_bid_micros`, `cpv_bid_micros`, `percent_cpc_bid_micros`, `bid_modifier` 0.1 to 10.0) | Micros | Ad group | SEARCH manual CPC | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupCriterion | No |
| Keyword URLs | `ad_group_criterion.final_urls[]`, `final_mobile_urls[]`, `final_url_suffix`, `tracking_url_template`, `url_custom_parameters[]` | A keyword final URL overrides the ad's | Ad group | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupCriterion, https://developers.google.com/google-ads/api/docs/ads/upgraded-urls/fields | No |
| Read-only | `effective_cpc_bid_micros` and `_source`, `quality_info`, `position_estimates`, `approval_status`, `disapproval_reasons[]`, `system_serving_status`, `primary_status`, `primary_status_reasons[]`, `labels[]` | Output only | Ad group | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupCriterion | Not applicable |

### 4.3 Responsive search ad

A responsive search ad is an `AdGroupAd` whose `ad.responsive_search_ad` holds the headlines and descriptions. Duplicate headline or description text fails with `AssetError.DUPLICATE_ASSET`, so remove repeats before sending. To pin, set `pinned_field` to `HEADLINE_1`, `HEADLINE_2`, `HEADLINE_3`, `DESCRIPTION_1` or `DESCRIPTION_2`; any other value returns `INVALID_PINNED_FIELD`, and every position must still be fillable or the request fails with `NOT_ENOUGH_AVAILABLE_ASSET_LINKS_FOR_VALID_COMBINATION`. The text can be changed after creation with `AdService.MutateAds`, and an update replaces the whole list. Since v23 one ad can no longer be shared across ad groups (`AD_SHARING_NOT_ALLOWED`). Call-only ads (`call_ad`) are not in the v25 `Ad` oneof and new ones cannot be created since 1 January 2026 (https://developers.google.com/google-ads/api/docs/responsive-search-ads/create-responsive-search-ads, https://developers.google.com/google-ads/api/docs/responsive-search-ads/overview, https://developers.google.com/google-ads/api/reference/rpc/v25/Ad, https://developers.google.com/google-ads/api/docs/deprecations, https://developers.google.com/google-ads/api/docs/release-notes).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Headlines | `ad_group_ad.ad.responsive_search_ad.headlines[].text` | 3 to 15, each at most 30 characters (wide CJK characters count as 2) | Ad | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/ResponsiveSearchAdInfo, https://developers.google.com/google-ads/api/docs/responsive-search-ads/create-responsive-search-ads, https://support.google.com/google-ads/answer/7684791 | Yes |
| Descriptions | `ad_group_ad.ad.responsive_search_ad.descriptions[].text` | 2 to 4, each at most 90 characters | Ad | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/ResponsiveSearchAdInfo, https://developers.google.com/google-ads/api/docs/responsive-search-ads/create-responsive-search-ads | Yes |
| Pinning | `...headlines[].pinned_field`, `...descriptions[].pinned_field` (`ServedAssetFieldType`) | `HEADLINE_1`, `HEADLINE_2`, `HEADLINE_3`, `DESCRIPTION_1`, `DESCRIPTION_2` | Ad | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/AdTextAsset, https://developers.google.com/google-ads/api/reference/rpc/v25/ServedAssetFieldTypeEnum.ServedAssetFieldType, https://developers.google.com/google-ads/api/docs/responsive-search-ads/overview | No |
| Per-asset read-outs | `...asset_performance_label`, `...policy_summary_info` | `BEST`, `GOOD`, `LOW`, `LEARNING`, `PENDING`, `NOT_APPLICABLE` | Ad | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/AdTextAsset, https://developers.google.com/google-ads/api/reference/rpc/v25/AssetPerformanceLabelEnum.AssetPerformanceLabel | Not applicable |
| Display path | `ad_group_ad.ad.responsive_search_ad.path1`, `path2` | At most 15 characters each; `path2` needs `path1` (`CANNOT_SET_PATH2_WITHOUT_PATH1`) | Ad | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/ResponsiveSearchAdInfo, https://developers.google.com/google-ads/api/docs/responsive-search-ads/create-responsive-search-ads | No |
| Final URLs | `ad_group_ad.ad.final_urls[]` | At least 1; at most 2,084 bytes each; the maximum count is not stated **(unconfirmed)** | Ad | All | https://developers.google.com/google-ads/api/reference/rpc/v25/Ad, https://developers.google.com/google-ads/api/docs/best-practices/system-limits | Yes |
| Other URL fields | `ad.final_mobile_urls[]`, `final_app_urls[]`, `tracking_url_template`, `final_url_suffix`, `url_custom_parameters[]`, `url_collections[]` | As in 2.4 | Ad | All | https://developers.google.com/google-ads/api/reference/rpc/v25/Ad | No |
| Display URL | `ad.display_url` | Used by some formats only; not by a responsive search ad **(unconfirmed)** | Ad | Not SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/Ad | No |
| Customizers in text | Inside `AdTextAsset.text`: `{CUSTOMIZER.name:default}`, `{KeyWord:default}`, `{LOCATION(City):default}`, `{COUNTDOWN(yyyy-MM-dd HH:mm:ss,daysBefore)}`, `{GLOBAL_COUNTDOWN(...)}` | Values come from a `CustomizerAttribute` linked at customer, campaign, ad group or keyword level. Work in headlines and descriptions, never in final URLs; non-countdown customizers also work in paths | Ad | SEARCH | https://developers.google.com/google-ads/api/docs/ads/customize-responsive-search-ads | No |

### 4.4 Ad Strength and Google-generated text

Ad Strength and its suggested fixes are output only. Google fills them in after the ad exists, and Ad Strength reads `PENDING` while it is worked out, so a launch flow can only show it by reading the ad back after creation. Google-generated headlines and descriptions are now called text customization (formerly "automatically created assets"). They are switched on per campaign with `asset_automation_settings` `TEXT_ASSET_AUTOMATION`, which on Search needs AI Max (2.5). Generated assets appear in `ad_group_ad_asset_view` with `source = AUTOMATICALLY_CREATED` and can be removed through the API. There is no API that returns Google's "suggested headlines" for an ad before it is created, other than `AssetGenerationService`, which is a closed beta (section 8).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Ad status | `ad_group_ad.status` | `ENABLED`, `PAUSED`, `REMOVED` | Ad | All | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupAdStatusEnum.AdGroupAdStatus | Yes, `ENABLED` |
| Ad Strength | `ad_group_ad.ad_strength` (output only) | `PENDING`, `NO_ADS`, `POOR`, `AVERAGE`, `GOOD`, `EXCELLENT` | Ad | SEARCH and others | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupAd, https://developers.google.com/google-ads/api/reference/rpc/v25/AdStrengthEnum.AdStrength | No (could be read back after launch) |
| Ad Strength fixes | `ad_group_ad.action_items[]` (output only) | Strings, such as advice to add more unique headlines | Ad | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupAd | No |
| Policy and status | `ad_group_ad.policy_summary`, `primary_status`, `primary_status_reasons[]`, `labels[]` (output only) | See 1.5 | Ad | All | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupAd | Not applicable |
| Ad dates | `ad_group_ad.start_date_time`, `end_date_time` (from v23.2) | `yyyy-MM-dd HH:mm:ss` in the account time zone; some ad types only | Ad | **(unconfirmed for responsive search ads)** | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupAd, https://developers.google.com/google-ads/api/docs/release-notes | No |
| Per-ad automation | `ad_group_ad.ad_group_ad_asset_automation_settings[].{asset_automation_type, asset_automation_status}` | Mostly Demand Gen types | Ad | DEMAND_GEN | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupAdAssetAutomationSetting | No |
| Remove generated text | `AdGroupAdService.RemoveAutomaticallyCreatedAssets` (ad level); `AutomaticallyCreatedAssetRemovalService.RemoveCampaignAutomaticallyCreatedAsset` (final URL expansion assets, from v21) | Not applicable | Ad, campaign | SEARCH | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupAdService/RemoveAutomaticallyCreatedAssets, https://developers.google.com/google-ads/api/docs/responsive-search-ads/overview | No |
| Asset view | `ad_group_ad_asset_view.{performance_label, pinned_field, field_type, source, enabled, policy_summary}` | `source`: `ADVERTISER`, `AUTOMATICALLY_CREATED` | Read only | SEARCH, DEMAND_GEN, MULTI_CHANNEL | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupAdAssetView, https://developers.google.com/google-ads/api/reference/rpc/v25/AssetSourceEnum.AssetSource | No |

### 4.5 Ad group and ad limits

| Limit | Value | Source |
|---|---|---|
| Headlines | 3 to 15, 30 characters each | https://developers.google.com/google-ads/api/docs/responsive-search-ads/create-responsive-search-ads, https://support.google.com/google-ads/answer/7684791 |
| Descriptions | 2 to 4, 90 characters each | Same |
| `path1`, `path2` | 15 characters each | Same |
| Wide characters (Chinese, Japanese, Korean) | Count as 2 characters | https://support.google.com/google-ads/answer/7684791 |
| Shown at serve time | Up to 3 headlines and 2 descriptions | https://developers.google.com/google-ads/api/docs/responsive-search-ads/overview |
| Enabled responsive search ads per ad group | 3 | https://support.google.com/google-ads/answer/6372658 |
| Active text-type ads per ad group | 50 | https://support.google.com/google-ads/answer/6372658 |
| Ad groups per campaign | 20,000 (100 for Local and App) | https://support.google.com/google-ads/answer/6372658 |
| Targeting items (keywords and others) per ad group | 20,000; 5 million per account | https://support.google.com/google-ads/answer/6372658 |
| Keyword text | 80 characters, 255 bytes, 10 words | https://developers.google.com/google-ads/api/reference/rpc/v25/KeywordInfo, https://developers.google.com/google-ads/api/docs/targeting/criteria |
| Ad group name | Under 255 full-width UTF-8 characters | https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroup |
| Enabled customizer attributes per account | 40 | https://developers.google.com/google-ads/api/docs/ads/customize-responsive-search-ads |

## 5. Assets

### 5.1 The Asset resource and AssetService

An asset is created with `AssetService.MutateAssets` (`POST https://googleads.googleapis.com/v25/customers/{customerId}/assets:mutate`) or, for PPCWay, with an `asset_operation` inside the atomic `GoogleAdsService.Mutate` ([as23], [as46]). `AssetOperation` has only `create` and `update`, with no `remove`, because "Assets are immutable and cannot be removed": to stop an asset serving, remove its link ([as22], [as23]). Exactly one member of the `asset_data` oneof is set ([as1]).

**`AssetType` in v25:** `APP_DEEP_LINK`, `BOOK_ON_GOOGLE`, `BUSINESS_MESSAGE`, `CALL`, `CALLOUT`, `CALL_TO_ACTION`, `DEMAND_GEN_CAROUSEL_CARD`, `DYNAMIC_CUSTOM`, `DYNAMIC_EDUCATION`, `DYNAMIC_FLIGHTS`, `DYNAMIC_HOTELS_AND_RENTALS`, `DYNAMIC_JOBS`, `DYNAMIC_LOCAL`, `DYNAMIC_REAL_ESTATE`, `DYNAMIC_TRAVEL`, `HOTEL_CALLOUT`, `HOTEL_PROPERTY`, `IMAGE`, `LEAD_FORM`, `LOCATION`, `MEDIA_BUNDLE`, `MOBILE_APP`, `PAGE_FEED`, `PRICE`, `PROMOTION`, `SITELINK`, `STRUCTURED_SNIPPET`, `TEXT`, `YOUTUBE_VIDEO`, `YOUTUBE_VIDEO_LIST` ([as2]).

**`AssetFieldType` in v25:** `AD_IMAGE`, `BOOK_ON_GOOGLE`, `BUSINESS_LOGO`, `BUSINESS_MESSAGE`, `BUSINESS_NAME`, `CALL`, `CALLOUT`, `CALL_TO_ACTION`, `CALL_TO_ACTION_SELECTION`, `CLASSIC_DISPLAY_IMAGE`, `DEMAND_GEN_CAROUSEL_CARD`, `DESCRIPTION`, `HEADLINE`, `HOTEL_CALLOUT`, `HOTEL_PROPERTY`, `LANDING_PAGE_PREVIEW`, `LANDSCAPE_LOGO`, `LEAD_FORM`, `LOGO`, `LONG_DESCRIPTION`, `LONG_HEADLINE`, `MANDATORY_AD_TEXT`, `MARKETING_IMAGE`, `MEDIA_BUNDLE`, `MOBILE_APP`, `PORTRAIT_MARKETING_IMAGE`, `PRICE`, `PROMOTION`, `RELATED_YOUTUBE_VIDEOS`, `SITELINK`, `SQUARE_MARKETING_IMAGE`, `STRUCTURED_SNIPPET`, `TALL_PORTRAIT_MARKETING_IMAGE`, `TEXT_DISCLAIMER` (v25.1), `VIDEO`, `YOUTUBE_VIDEO` ([as3], [as45]).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Name | `asset.name` | Optional. Image and media bundle names must be unique: a duplicate gets a suffix, and the name is dropped if the content matches an existing asset | Account asset library | All | [as1], [as29] | No |
| Type | `asset.type` | Output only; follows from the `asset_data` member set | Asset | All | [as1], [as2] | No |
| Final URLs | `asset.final_urls[]`, `asset.final_mobile_urls[]` | Used by link assets such as sitelink and promotion | Asset | All | [as1] | No |
| URL options | `asset.tracking_url_template`, `asset.url_custom_parameters[]`, `asset.final_url_suffix` | As in 2.4 | Asset | All | [as1] | No |
| Policy | `asset.policy_summary`, `asset.field_type_policy_summaries[]` | Output only | Asset | All | [as1] | No |
| Synthetic content | `asset.synthetic_content_info` | Updatable for `IMAGE`, `MEDIA_BUNDLE`, `YOUTUBE_VIDEO`; fully mutable from v25 | Asset | All | [as1], [as45] | No |

### 5.2 Asset types relevant to creation

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Sitelink | `asset.sitelink_asset.link_text`, `.description1`, `.description2`, `.start_date`, `.end_date`, `.ad_schedule_targets[]`; landing page in `asset.final_urls` | `link_text` required, 1 to 25 characters. `description1` and `description2` 1 to 35 each, both or neither. Dates `yyyy-MM-dd`. Field type `SITELINK` | Customer, campaign, ad group | SEARCH, PERFORMANCE_MAX, VIDEO, DEMAND_GEN | [as4], [as28], [as34] | No |
| Callout | `asset.callout_asset.callout_text`, `.start_date`, `.end_date`, `.ad_schedule_targets[]` | `callout_text` required, 1 to 25. Field type `CALLOUT` | Customer, campaign, ad group | SEARCH (Help) | [as5], [as28], [as35] | No |
| Structured snippet | `asset.structured_snippet_asset.header`, `.values[]` | `header` from a fixed list (English: Brands, Amenities, Styles, Types, Destinations, Service catalog, Courses, Neighborhoods, Shows, Insurance coverage, Degree programs, Featured hotels, Models). `values` 3 to 10, each 1 to 25. Field type `STRUCTURED_SNIPPET` | Customer, campaign, ad group | SEARCH | [as6], [as7], [as28], [as36] | No |
| Image | `asset.image_asset.data` (bytes, base64 over REST), `.file_size`, `.mime_type`, `.full_size` | At most 5,120 KB. Performance Max accepts GIF, JPG, PNG; Search image assets accept PNG and JPG. Aspect ratio is checked when the image is linked, not when uploaded (`ASPECT_RATIO_NOT_ALLOWED`) | Linked per field type | All image formats | [as8], [as22], [pm3], [as37] | No |
| Search image | `campaign_asset` or `ad_group_asset` with `field_type = AD_IMAGE` | Square 1:1 required (minimum 300 by 300, recommended 1200 by 1200); landscape 1.91:1 optional (minimum 600 by 314). Up to 20 per campaign. Account eligibility rules apply (account at least 60 days old, good policy history, recent Search spend) | Campaign, ad group | SEARCH | [as28], [as37], [as31] | No |
| Business name | `asset.text_asset.text` linked with `field_type = BUSINESS_NAME` | 25 characters. Search: one per account and one per campaign. Performance Max: one per campaign | Customer, campaign (Search); campaign or asset group (Performance Max) | SEARCH, PERFORMANCE_MAX | [as28], [as38], [pm3] | No |
| Business logo | `asset.image_asset` linked as `BUSINESS_LOGO` (Search) or `LOGO` (Performance Max) | Search: one per account and one per campaign; Search size rules **(unconfirmed)**. Performance Max `LOGO`: 1:1, minimum 128 by 128, up to 5 | Customer, campaign | SEARCH, PERFORMANCE_MAX | [as28], [as38], [pm3] | No |
| Call | `asset.call_asset.country_code`, `.phone_number`, `.call_conversion_reporting_state`, `.call_conversion_action`, `.ad_schedule_targets[]` | `country_code` (such as "US") and `phone_number` required. Reporting state `DISABLED`, `USE_ACCOUNT_LEVEL_CALL_CONVERSION_ACTION`, `USE_RESOURCE_LEVEL_CALL_CONVERSION_ACTION`; `call_conversion_action` only with the resource-level state. The number must be verified. Field type `CALL` | Customer, campaign, ad group | SEARCH | [as9], [as10], [as28], [as41] | No |
| Lead form | `asset.lead_form_asset.business_name`, `.call_to_action_type`, `.call_to_action_description`, `.headline`, `.description`, `.privacy_policy_url` (all required); `.fields[]`, `.custom_question_fields[]`, `.delivery_methods[]`, `.post_submit_headline`, `.post_submit_description`, `.post_submit_call_to_action_type`, `.background_image_asset`, `.desired_intent`, `.custom_disclosure` | Up to 5 custom questions; single-choice questions take 2 to 12 answers; one webhook delivery; background image exactly 1200 by 628; `custom_disclosure` allowlist only. Character limits **(unconfirmed)**. Field type `LEAD_FORM` | Campaign only | SEARCH, PERFORMANCE_MAX | [as11], [as21], [as28], [as39] | No |
| Price | `asset.price_asset.type` (required), `.price_qualifier`, `.language_code` (required), `.price_offerings[]` with `.header`, `.description`, `.price`, `.unit`, `.final_url`, `.final_mobile_url` | 3 to 8 offerings; `header` and `description` required, 1 to 25 each; `price` and `final_url` required. `type`: `BRANDS`, `EVENTS`, `LOCATIONS`, `NEIGHBORHOODS`, `PRODUCT_CATEGORIES`, `PRODUCT_TIERS`, `SERVICES`, `SERVICE_CATEGORIES`, `SERVICE_TIERS`. Field type `PRICE` | Customer, campaign, ad group | SEARCH **(unconfirmed)** | [as12], [as13], [as14], [as28] | No |
| Promotion | `asset.promotion_asset.promotion_target` (required), `.discount_modifier`, one of `.percent_off` or `.money_amount_off` (required), one of `.promotion_code`, `.orders_over_amount`, `.promotion_barcode_info`, `.promotion_qr_code_info`, `.occasion`, `.language_code`, `.start_date`, `.end_date`, `.redemption_start_date`, `.redemption_end_date`, `.terms_and_conditions_text`, `.terms_and_conditions_uri`, `.ad_schedule_targets[]` | `percent_off` uses 1,000,000 for 100 percent; `discount_modifier` `UP_TO`. Field type `PROMOTION` | Customer, campaign, ad group | SEARCH, VIDEO, PERFORMANCE_MAX (store goals) | [as15], [as16], [as28], [as40] | No |
| Mobile app | `asset.mobile_app_asset.app_id`, `.app_store`, `.link_text`, `.start_date`, `.end_date` | `app_id`, `app_store` and `link_text` (1 to 25) required. Field type `MOBILE_APP` | Customer, campaign, ad group | SEARCH **(unconfirmed)** | [as17], [as21], [as28] | No |
| Location | `asset.location_asset.place_id`, `.location_ownership_type`, `.business_profile_locations[]` | Output only. Created automatically when an `asset_set` of type `LOCATION_SYNC` is synced (5.4) | Customer, campaign, ad group, through asset sets | SEARCH, PERFORMANCE_MAX | [as1], [as18], [as30] | No |
| Text | `asset.text_asset.text` | Immutable. Length depends on the field type: `HEADLINE` 30, `LONG_HEADLINE` 90, `DESCRIPTION` 90, `BUSINESS_NAME` 25. Responsive search ad text is inline, not an asset | Asset group, campaign | PERFORMANCE_MAX, DEMAND_GEN, DISPLAY | [as19], [as22], [as29], [pm3] | No |
| YouTube video | `asset.youtube_video_asset.youtube_video_id`, `.youtube_video_title` | Immutable; the 11-character id from the YouTube URL. Field type `YOUTUBE_VIDEO` | Asset group | PERFORMANCE_MAX, VIDEO, DEMAND_GEN | [as20], [as21], [as22] | No |
| Call to action | `asset.call_to_action_asset.call_to_action` | `APPLY_NOW`, `BOOK_NOW`, `BUY_NOW`, `CONTACT_US`, `DONATE_NOW`, `DOWNLOAD`, `GET_QUOTE`, `LEARN_MORE`, `ORDER_NOW`, `PLAY_NOW`, `SEE_MORE`, `SHOP_NOW`, `SIGN_UP`, `START_NOW`, `SUBSCRIBE`, `VISIT_SITE`, `WATCH_NOW`. Field type `CALL_TO_ACTION_SELECTION` (at most 1) | Asset group | PERFORMANCE_MAX | [as21], [as22], [as44], [pm3] | No |
| Demand Gen carousel card | `asset.demand_gen_carousel_card_asset.marketing_image_asset` or `.square_marketing_image_asset` (at least one), `.portrait_marketing_image_asset`, `.headline` (required), `.call_to_action_text` | Immutable. Field type `DEMAND_GEN_CAROUSEL_CARD` | Ad | DEMAND_GEN | [as1], [as21] | No |
| Business message | `asset.business_message_asset.message_provider`, `.starter_message` (required), `.call_to_action` | One active asset per provider per level. Field type `BUSINESS_MESSAGE` | Customer, campaign, ad group | **(unconfirmed)** | [as21], [as28] | No |
| Page feed | `asset.page_feed_asset.page_url` (required), `.labels[]` | Grouped in an `asset_set` of type `PAGE_FEED`, linked with `campaign_asset_set` | Campaign asset set | SEARCH (AI Max), PERFORMANCE_MAX | [as21], [as28], [pm6] | No |

### 5.3 What can change after creation, and images over REST

These asset types can be updated with an `update_mask`: business message, lead form, promotion, callout, structured snippet, sitelink, mobile app, hotel callout, call and price. These cannot: text (and so business name), image (ad image, logo), YouTube video, call to action, Demand Gen carousel card, media bundle, app deep link, hotel property and YouTube video list; to change one, create a new asset and re-link it ([as28], [as23], [as22], [as29]). On links, `asset`, `field_type`, `campaign` and `ad_group` are immutable; only `status` can change. One oddity: the proto marks `image_asset` as output only, yet Google's samples create images by setting `image_asset.data` ([as1], [as22], [as29]).

REST sends `bytes` as standard base64 with padding, int64 as a decimal string, enums by name and field names in lowerCamelCase ([as32], [as33]). An image create inside the atomic request looks like this:

```json
POST https://googleads.googleapis.com/v25/customers/{customerId}/googleAds:mutate
{"mutateOperations": [{"assetOperation": {"create": {
  "resourceName": "customers/{customerId}/assets/-10",
  "name": "Hero landscape 1200x628 v1",
  "imageAsset": {"data": "<base64 of PNG or JPG bytes>"}}}}]}
```

### 5.4 Linking at customer, campaign and ad group level

Each link names one asset in one role (`field_type`). For Search callouts, snippets, calls, prices and promotions, the most specific level wins; sitelinks from every level of the same branch can serve together. Location assets are linked through asset sets, never through the link resources ([as24], [as25], [as26], [as34], [as35], [as30]).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Account link | `customer_asset.asset`, `.field_type` (both required, immutable), `.status`; resource `customers/{cid}/customerAssets/{asset_id}~{field_type}` | Status `ENABLED`, `PAUSED`, `REMOVED`. Valid field types: `SITELINK`, `CALLOUT`, `STRUCTURED_SNIPPET`, `CALL`, `PRICE`, `PROMOTION`, `MOBILE_APP`, `HOTEL_CALLOUT`, `BUSINESS_MESSAGE`, `BUSINESS_NAME`, `BUSINESS_LOGO` | Customer | SEARCH and others | [as24], [as27], [as28] | No |
| Campaign link | `campaign_asset.campaign`, `.asset` (immutable), `.field_type` (required, immutable), `.status`; resource `customers/{cid}/campaignAssets/{campaign_id}~{asset_id}~{field_type}` | All the account-level types plus `AD_IMAGE` and `LEAD_FORM` (campaign only). Performance Max brand guidelines use `BUSINESS_NAME`, `LOGO`, `LANDSCAPE_LOGO` | Campaign | SEARCH, PERFORMANCE_MAX | [as25], [as28], [pm3] | No |
| Ad group link | `ad_group_asset.ad_group`, `.asset`, `.field_type` (all required, immutable), `.status`; resource `customers/{cid}/adGroupAssets/{ad_group_id}~{asset_id}~{field_type}` | `SITELINK`, `CALLOUT`, `STRUCTURED_SNIPPET`, `CALL`, `PRICE`, `PROMOTION`, `MOBILE_APP`, `HOTEL_CALLOUT`, `BUSINESS_MESSAGE`, `AD_IMAGE` | Ad group | SEARCH | [as26], [as28] | No |
| Asset group link | `asset_group_asset` (section 6) | Performance Max field types | Asset group | PERFORMANCE_MAX | [as29], [pm28] | No |
| Location sync | `asset_set.type = LOCATION_SYNC`, `asset_set.location_set.location_ownership_type` (`BUSINESS_OWNER` or `AFFILIATE`), one of `.business_profile_location_set` (needs an OAuth token with the `business.manage` scope), `.chain_location_set`, `.maps_location_set`; attached with `customer_asset_set` | Only one enabled `LOCATION_SYNC` set per customer; location assets are generated from it | Customer | SEARCH, PERFORMANCE_MAX | [as30] | No |
| Location subset | `asset_set.type` = `BUSINESS_PROFILE_DYNAMIC_LOCATION_GROUP`, `CHAIN_DYNAMIC_LOCATION_GROUP` or `STATIC_LOCATION_GROUP`, attached with `campaign_asset_set` or `ad_group_asset_set` | Dynamic groups are not possible with a maps location set | Campaign, ad group | SEARCH, PERFORMANCE_MAX | [as28], [as30] | No |
| Block inherited assets | `campaign.excluded_parent_asset_field_types[]`, `campaign.excluded_parent_asset_set_types[]` | Field type list; asset set types `LOCATION_SYNC` only | Campaign | All | [pm13] | No |

### 5.5 Asset limits

v25 names a per-level cap for each extension type (for example `SITELINK_CAMPAIGN_ASSETS_PER_CAMPAIGN`), but Google does not publish the numbers in the API docs ([as31]).

| Limit | Value | Source |
|---|---|---|
| Sitelink `link_text` | 1 to 25 characters (12 in double-width languages) | [as4], [as34] |
| Sitelink descriptions | 35 characters each; both or neither | [as4] |
| Sitelinks per customer, campaign or ad group | 20 **(unconfirmed; a forum report shows the limit hit at ad group level)** | [as31], [as43] |
| Sitelinks shown per ad | At least 2 to show; up to 6 on desktop, 8 on mobile | [as34] |
| Callout text | 1 to 25 characters; up to 10 shown per ad; per-level cap **(unconfirmed)** | [as5], [as35] |
| Structured snippet values | 3 to 10, 25 characters each; per-level cap **(unconfirmed)** | [as6] |
| Ad schedules per sitelink, callout, call or promotion | 6 per day, 42 in total | [as4], [as5], [as9], [as15] |
| Search `AD_IMAGE` per campaign | 1 square required; 20 in total; 5,120 KB | [as37] |
| Business name and logo (Search) | 1 per account and 1 per campaign; name 25 characters | [as38], [pm3] |
| Price offerings | 3 to 8; header and description 25 each | [as12], [as13] |
| Lead form custom questions | Up to 5; character limits **(unconfirmed)** | [as11] |
| Mobile app link text | 1 to 25 characters | [as17] |
| YouTube video id | 11 characters | [as20] |
| Image file size | 5,120 KB | [pm3], [as37] |
| Location asset sets | 20 per campaign, 20 per ad group, 5 per asset group, 20 per account | [as42] |
| Asset links per account | 50,000 campaign-level; 250,000 ad group-level; 10,000 ad group-level per campaign | [as42] |

[as1]: https://developers.google.com/google-ads/api/reference/rpc/v25/Asset
[as2]: https://developers.google.com/google-ads/api/reference/rpc/v25/AssetTypeEnum.AssetType
[as3]: https://developers.google.com/google-ads/api/reference/rpc/v25/AssetFieldTypeEnum.AssetFieldType
[as4]: https://developers.google.com/google-ads/api/reference/rpc/v25/SitelinkAsset
[as5]: https://developers.google.com/google-ads/api/reference/rpc/v25/CalloutAsset
[as6]: https://developers.google.com/google-ads/api/reference/rpc/v25/StructuredSnippetAsset
[as7]: https://developers.google.com/google-ads/api/reference/data/structured-snippet-headers
[as8]: https://developers.google.com/google-ads/api/reference/rpc/v25/ImageAsset
[as9]: https://developers.google.com/google-ads/api/reference/rpc/v25/CallAsset
[as10]: https://developers.google.com/google-ads/api/reference/rpc/v25/CallConversionReportingStateEnum.CallConversionReportingState
[as11]: https://developers.google.com/google-ads/api/reference/rpc/v25/LeadFormAsset
[as12]: https://developers.google.com/google-ads/api/reference/rpc/v25/PriceAsset
[as13]: https://developers.google.com/google-ads/api/reference/rpc/v25/PriceOffering
[as14]: https://developers.google.com/google-ads/api/reference/rpc/v25/PriceExtensionTypeEnum.PriceExtensionType
[as15]: https://developers.google.com/google-ads/api/reference/rpc/v25/PromotionAsset
[as16]: https://developers.google.com/google-ads/api/reference/rpc/v25/PromotionExtensionDiscountModifierEnum.PromotionExtensionDiscountModifier
[as17]: https://developers.google.com/google-ads/api/reference/rpc/v25/MobileAppAsset
[as18]: https://developers.google.com/google-ads/api/reference/rpc/v25/LocationAsset
[as19]: https://developers.google.com/google-ads/api/reference/rpc/v25/TextAsset
[as20]: https://developers.google.com/google-ads/api/reference/rpc/v25/YoutubeVideoAsset
[as21]: https://raw.githubusercontent.com/googleapis/googleapis/master/google/ads/googleads/v25/common/asset_types.proto
[as22]: https://raw.githubusercontent.com/googleapis/googleapis/master/google/ads/googleads/v25/resources/asset.proto
[as23]: https://raw.githubusercontent.com/googleapis/googleapis/master/google/ads/googleads/v25/services/asset_service.proto
[as24]: https://developers.google.com/google-ads/api/reference/rpc/v25/CustomerAsset
[as25]: https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignAsset
[as26]: https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupAsset
[as27]: https://developers.google.com/google-ads/api/reference/rpc/v25/AssetLinkStatusEnum.AssetLinkStatus
[as28]: https://developers.google.com/google-ads/api/docs/assets/overview
[as29]: https://developers.google.com/google-ads/api/docs/assets/working-with-assets
[as30]: https://developers.google.com/google-ads/api/docs/assets/location-assets
[as31]: https://developers.google.com/google-ads/api/reference/rpc/v25/ResourceLimitTypeEnum.ResourceLimitType
[as32]: https://protobuf.dev/programming-guides/json/
[as33]: https://developers.google.com/google-ads/api/rest/design/json-mappings
[as34]: https://support.google.com/google-ads/answer/2375416
[as35]: https://support.google.com/google-ads/answer/6079510
[as36]: https://support.google.com/google-ads/answer/6280012
[as37]: https://support.google.com/google-ads/answer/9566341
[as38]: https://support.google.com/google-ads/answer/12497613
[as39]: https://support.google.com/google-ads/answer/9423234
[as40]: https://support.google.com/google-ads/answer/7367521
[as41]: https://support.google.com/google-ads/answer/2453991
[as42]: https://support.google.com/google-ads/answer/6372658
[as43]: https://groups.google.com/g/adwords-api/c/uwZGYSH_vZc
[as44]: https://developers.google.com/google-ads/api/reference/rpc/v25/CallToActionTypeEnum.CallToActionType
[as45]: https://developers.google.com/google-ads/api/docs/release-notes
[as46]: https://developers.google.com/google-ads/api/reference/rpc/v25/MutateOperation

## 6. Performance Max specifics

### 6.1 Campaign requirements

A Performance Max campaign sets `advertising_channel_type = PERFORMANCE_MAX` and leaves the sub-type unset. Bidding must be a standard (not portfolio) `maximize_conversions` or `maximize_conversion_value`, each with an optional target. The budget must be daily, standard delivery and not shared. Conversion tracking must already exist on the account ([pm1], [pm2]). Brand guidelines are on by default for new campaigns from v21; the switch is immutable, so they can be turned on later with `CampaignService.EnablePMaxBrandGuidelines` but never off ([pm2], [pm14], [pm54]). URL expansion is controlled by an asset automation setting, because `campaign.url_expansion_opt_out` was removed in v22 ([pm23], [pm54]).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Channel | `campaign.advertising_channel_type` | `PERFORMANCE_MAX`; sub-type unset | Campaign | PERFORMANCE_MAX | [pm1], [pm2] | No |
| Bidding | `campaign.maximize_conversions.target_cpa_micros` (optional) or `campaign.maximize_conversion_value.target_roas` (optional) | No portfolio strategies; no maximize clicks | Campaign | PERFORMANCE_MAX | [pm1], [pm2], [pm14] | No |
| Budget | `campaign_budget.explicitly_shared`, `.period`, `.delivery_method` | `false`, `DAILY`, `STANDARD` | Budget | PERFORMANCE_MAX | [pm1] | No |
| Status | `campaign.status` | `PAUSED` recommended. The guide calls the campaign "the only entity in the mutate request that should have its status set" | Campaign | PERFORMANCE_MAX | [pm2] | No |
| EU political declaration | `campaign.contains_eu_political_advertising` | As in 2.1; required since v21 | Campaign | All | [pm2], [pm13], [pm54] | No |
| Brand guidelines switch | `campaign.brand_guidelines_enabled` | bool, immutable, default true for new standard and retail campaigns. Not for travel goals or Local Services. To turn on later: `CampaignService.EnablePMaxBrandGuidelines` with `auto_populate_brand_assets` or `brand_assets`, at most 10 operations per request | Campaign | PERFORMANCE_MAX | [pm2], [pm14], [pm54] | No |
| Brand style | `campaign.brand_guidelines.main_color`, `.accent_color`, `.predefined_font_family` | As in 2.5 | Campaign | PERFORMANCE_MAX | [pm18] | No |
| Brand assets | `campaign_asset` with `field_type` `BUSINESS_NAME`, `LOGO`, `LANDSCAPE_LOGO` | Exactly 1 `BUSINESS_NAME` and at least 1 `LOGO`, with up to 4 more logos; `LOGO` and `LANDSCAPE_LOGO` share one cap of 5. Must be in the same request as the campaign, with partial failure off | Campaign | PERFORMANCE_MAX | [pm2], [pm3], [as31] | No |
| Asset automation | `campaign.asset_automation_settings[].{asset_automation_type, asset_automation_status, automated_video_crawl_setting}` | `OPTED_IN` or `OPTED_OUT`. Performance Max defaults: `FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION` on, `TEXT_ASSET_AUTOMATION` on, `GENERATE_ENHANCED_YOUTUBE_VIDEOS` on, `GENERATE_IMAGE_ENHANCEMENT` on, `GENERATE_IMAGE_EXTRACTION` follows the account's dynamic image setting (changeable only in the Google Ads UI), `AUTOMATED_VIDEO_CRAWL` off (v25.2) | Campaign | PERFORMANCE_MAX | [pm12], [pm15], [pm16], [pm17], [pm53] | No |
| Final URL expansion off | `asset_automation_settings` entry `FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION` set to `OPTED_OUT` | Replaces `url_expansion_opt_out` (removed in v22). Asset group final URLs are expandable unless opted out | Campaign | PERFORMANCE_MAX | [pm23], [pm54], [pm25] | No |
| Text guidelines | `campaign.text_guidelines.term_exclusions[]`, `.messaging_restrictions[]` | As in 2.5 (v23.1) | Campaign | PERFORMANCE_MAX, SEARCH | [pm19], [pm20], [pm6], [pm53] | No |
| Performance Max settings | `campaign.pmax_campaign_settings.brand_targeting_overrides.ignore_exclusions_for_shopping_ads`; `.local_services_enabled` (output only in v25) | bool | Campaign | PERFORMANCE_MAX | [pm21], [pm22] | No |
| Retail feed | `campaign.shopping_setting.merchant_id` (required for retail), `.feed_label`, `.campaign_priority`, `.enable_local`; `campaign.listing_type` | Merchant Center must be linked first (section 9) | Campaign | PERFORMANCE_MAX retail | [pm9], [pm13] | No |
| Page feed for text | `asset_set` of type `PAGE_FEED` linked with `campaign_asset_set`, plus `TEXT_ASSET_AUTOMATION` opted in | Both in the same request, or `OPERATION_NOT_PERMITTED_FOR_CONTEXT` | Campaign | PERFORMANCE_MAX | [pm6] | No |

### 6.2 AssetGroupService

An asset group belongs to one campaign; a campaign holds at most 100 ([pm4], [pm36]). In a non-retail campaign an asset group cannot be created on its own: "an AssetGroup and all associated AssetGroupAsset objects must be created in the same bulk mutate request", and "Partial failure is not supported" ([pm4]).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Name | `asset_group.name` | Required, 1 to 128 characters, unique in the campaign (`DUPLICATE_NAME`) | Asset group | PERFORMANCE_MAX | [pm24], [pm25], [pm27] | No |
| Campaign | `asset_group.campaign` | Immutable | Asset group | PERFORMANCE_MAX | [pm24] | No |
| Final URLs | `asset_group.final_urls[]`, `.final_mobile_urls[]` | At least one final URL (`FINAL_URL_REQUIRED`), except Local Services and retail groups without assets. Retail URLs must match the Merchant Center domain. The final URL cannot be excluded by webpage criteria | Asset group | PERFORMANCE_MAX | [pm4], [pm27] | No |
| Display path | `asset_group.path1`, `.path2` | `path2` needs `path1` (`PATH1_REQUIRED_WHEN_PATH2_IS_SET`); 15 characters each **(unconfirmed)** | Asset group | PERFORMANCE_MAX | [pm25], [pm27] | No |
| Status | `asset_group.status` | `ENABLED`, `PAUSED`, `REMOVED` | Asset group | PERFORMANCE_MAX | [pm26] | No |
| URL options | `asset_group.tracking_url_template`, `.url_custom_parameters[]`, `.final_url_suffix` | Added in v25.2 | Asset group | PERFORMANCE_MAX | [pm25], [pm53] | No |
| Read-only state | `asset_group.ad_strength`, `.asset_coverage`, `.primary_status`, `.primary_status_reasons[]` | Output only | Asset group | PERFORMANCE_MAX | [pm24] | No |

### 6.3 AssetGroupAssetService and asset counts

`asset_group_asset.asset_group` and `.asset` are immutable; set `.field_type` and `.status`. The resource name is `customers/{cid}/assetGroupAssets/{asset_group_id}~{asset_id}~{field_type}` ([pm28]). With brand guidelines on, `BUSINESS_NAME`, `LOGO` and `LANDSCAPE_LOGO` go on `campaign_asset`, not on the asset group ([pm3]). A retail asset group may have no custom assets, but if it has any it needs every minimum in one request ([pm3], [pm4]). Missing minimums fail with `AssetGroupError` values `NOT_ENOUGH_HEADLINE_ASSET`, `NOT_ENOUGH_LONG_HEADLINE_ASSET`, `NOT_ENOUGH_DESCRIPTION_ASSET`, `SHORT_DESCRIPTION_REQUIRED`, `NOT_ENOUGH_MARKETING_IMAGE_ASSET`, `NOT_ENOUGH_SQUARE_MARKETING_IMAGE_ASSET`, `NOT_ENOUGH_LOGO_ASSET`, `NOT_ENOUGH_BUSINESS_NAME_ASSET` ([pm27]).

| Field type | Minimum | Maximum | Character limit or format | Source |
|---|---|---|---|---|
| `HEADLINE` | 3 | 15 | 30 characters. Help also asks for one headline of 15 characters or fewer (not in the API docs) | [pm3], [pm47] |
| `LONG_HEADLINE` | 1 | 5 | 90 characters | [pm3], [pm47] |
| `DESCRIPTION` | 2 | 5 | 90 characters; at least one short description required (`SHORT_DESCRIPTION_REQUIRED`), which Help defines as 60 characters or fewer | [pm3], [pm27], [pm50] |
| `BUSINESS_NAME` | 1 | 1 | 25 characters; on the asset group only when brand guidelines are off, otherwise on the campaign | [pm2], [pm3] |
| `MARKETING_IMAGE` | 1 | 20 | 1.91:1, minimum 600 by 314 | [pm3], [pm48] |
| `SQUARE_MARKETING_IMAGE` | 1 | 20 | 1:1, minimum 300 by 300 | [pm3], [pm48] |
| `PORTRAIT_MARKETING_IMAGE` | 0 | 20 | 4:5, minimum 480 by 600 | [pm3], [pm48] |
| `LOGO` | 1 | 5 | 1:1, minimum 128 by 128 | [pm3], [pm48] |
| `LANDSCAPE_LOGO` | 0 | 20 per the API page, 5 per Help; with brand guidelines, `LOGO` plus `LANDSCAPE_LOGO` share a cap of 5 | 4:1, minimum 512 by 128 | [pm3], [pm48], [pm2], [as31] |
| `YOUTUBE_VIDEO` | 0 | 15 | 16:9, 1:1 or 9:16, at least 10 seconds | [pm3], [pm49] |
| `CALL_TO_ACTION_SELECTION` | 0 | 1 | Enum value | [pm3] |
| `MEDIA_BUNDLE` | 0 | 1 | Under 150 KB | [pm3] |
| Images overall | Not applicable | The API gives 20 per image field type and no combined total | 5,120 KB; GIF, JPG, PNG | [pm3] |

### 6.4 Asset group signals and search themes

Standard Performance Max campaigns run without signals. Signals can only be added or removed (removing the last one fails with `CANNOT_REMOVE_ALL_SIGNALS` where signals are required), and each signal sets exactly one immutable member ([pm7], [pm29]).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Audience signal | `asset_group_signal.asset_group`, `.audience.audience` | Resource name of an `audience` (created with `audience_operation`; `ASSET_GROUP` scope allowed). Resource `customers/{cid}/assetGroupSignals/{asset_group_id}~{signal_id}` | Asset group | PERFORMANCE_MAX | [pm7], [pm29], [as46] | No |
| Search theme | `asset_group_signal.search_theme.text` | Keyword-like text; `approval_status` and `disapproval_reasons[]` are output only. Errors include `TOO_MANY_WORDS`, `SEARCH_THEME_POLICY_VIOLATION`, `RESOURCE_LIMIT`. Up to 50 per asset group per Help (older Help pages say 25); text limits not published **(unconfirmed)** | Asset group | PERFORMANCE_MAX only | [pm29], [pm30], [pm31], [pm51] | No |
| Local Services id | `asset_group_signal.local_services_id` | Allowlist only | Asset group | PERFORMANCE_MAX Local Services | [pm7], [pm29] | No |
| Vertical item rules | `asset_group_signal.vertical_ads_item_group_rule_list` | Shared set of type `VERTICAL_ADS_ITEM_GROUP_RULE_LIST`; allowlist only, v24.2 | Asset group | PERFORMANCE_MAX vertical | [pm29], [pm53] | No |

### 6.5 Listing group filters (retail), brand exclusions and URL exclusions

Every asset group in a retail campaign needs a valid tree of `AssetGroupListingGroupFilter` nodes: "Ads won't serve until you create a valid listing group tree". A single node covers all products: a root of type `UNIT_INCLUDED`, `listing_source` `SHOPPING`, with no `case_value` and no parent. Each subdivision must be fully partitioned with an "everything else" node, created in the same request ([pm8], [pm37]). On Performance Max, `BRAND` and `KEYWORD` criteria are negative only; `WEBPAGE`, `LOCATION`, `LOCATION_GROUP`, `LANGUAGE`, `AD_SCHEDULE`, `DEVICE` and `AGE_RANGE` can be positive or negative ([pm10]).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Listing group node | `asset_group_listing_group_filter.asset_group`, `.type`, `.listing_source`, `.parent_listing_group_filter` (all immutable), `.case_value`; resource `customers/{cid}/assetGroupListingGroupFilters/{asset_group_id}~{listing_group_filter_id}` | Root has no parent and no `case_value` | Asset group | PERFORMANCE_MAX retail | [pm32] | No |
| Node type | `.type` | `SUBDIVISION`, `UNIT_INCLUDED`, `UNIT_EXCLUDED` | Asset group | PERFORMANCE_MAX retail | [pm33] | No |
| Listing source | `.listing_source` | `SHOPPING`, `WEBPAGE`, `RETAIL` | Asset group | PERFORMANCE_MAX | [pm34] | No |
| Dimension | `.case_value.<member>` | `product_brand`, `product_category`, `product_channel`, `product_condition`, `product_custom_attribute`, `product_item_id`, `product_type`, `retail_filter_bundle` (allowlist), `webpage` | Asset group | PERFORMANCE_MAX retail | [pm35], [pm53] | No |
| Brand list | `shared_set.type = BRANDS`; `shared_criterion.brand.entity_id` (from `BrandSuggestionService.SuggestBrands`) | Brands to exclude | Shared set | PERFORMANCE_MAX, SEARCH | [pm41], [pm42], [pm43], [pm45] | No |
| Brand exclusion | `campaign_criterion.brand_list.shared_set` with `negative = true` | Negative only on Performance Max; Shopping ads can ignore it (`brand_targeting_overrides.ignore_exclusions_for_shopping_ads`) | Campaign | PERFORMANCE_MAX | [pm10], [pm39], [pm40], [pm22] | No |
| URL exclusion | `campaign_criterion.webpage.criterion_name` (required on create), `.webpage.conditions[]`, `negative = true` | Excludes pages from final URL expansion; the asset group's final URL cannot be excluded. The `WEBPAGES` shared set and `webpage_list` are not public | Campaign | PERFORMANCE_MAX | [pm10], [pm4], [pm39], [pm41] | No |
| Campaign negative keyword | `campaign_criterion.keyword.{text, match_type}`, `negative = true` | Up to 10,000 per campaign (from v20) | Campaign | PERFORMANCE_MAX | [pm10], [pm54] | No |
| Account negative keywords | `shared_set.type = ACCOUNT_LEVEL_NEGATIVE_KEYWORDS`, `customer_negative_criterion.negative_keyword_list.shared_set` | One set per account, 1,000 keywords | Account | PERFORMANCE_MAX, SEARCH and others | [pm44], [pm45], [pm52] | No |
| Other criteria | `campaign_criterion.location`, `.location_group`, `.language`, `.ad_schedule`, `.device`, `.age_range`, `.gender` | Positive or negative; gender exclusion only (v24). No location criterion means all regions. Language applies outside Search only | Campaign | PERFORMANCE_MAX | [pm10], [pm39], [pm53] | No |
| IP and placement exclusions | `campaign_criterion.ip_block`, `customer_negative_criterion.placement_list` | Not in the Performance Max criteria list **(unconfirmed)** | Campaign, account | **(unconfirmed)** | [pm39], [pm44], [pm10] | No |

### 6.6 Performance Max limits

| Limit | Value | Source |
|---|---|---|
| Asset groups per campaign | 1 to 100 | [pm4], [pm36] |
| Performance Max campaigns per account | 100 | [pm36] |
| Listing group filters per asset group | 1,000; tree depth 7 (`TREE_TOO_DEEP`) | [pm36], [pm8] |
| Negative keywords per campaign | 10,000 | [pm10] |
| Search themes per asset group | 50 per Help (older pages say 25) **(unconfirmed in the API docs)** | [pm51] |
| `EnablePMaxBrandGuidelines` operations per request | 10 | [pm2] |
| Location asset sets per asset group | 5 | [as42] |

### 6.7 Required atomic creation order (Google's guide)

Google's Performance Max guide says to order operations so nothing is referenced before it is created, and to put every `asset_operation` before the contiguous run of `asset_group_asset_operation`s; interleaving them makes the server check the minimums too early and fails the whole request. The campaign and its brand-guideline `campaign_asset`s must be in one request, and so must the asset group and its asset links ([pm5], [pm4], [pm1]). Google's own samples deviate (the standard Python sample creates text assets in earlier requests and pairs each remaining asset with its link; the retail sample puts the listing group filter straight after the asset group) ([pm38], [pm37]). Follow the guide's grouping. The full sequence is in section 11.2.

[pm1]: https://developers.google.com/google-ads/api/performance-max/getting-started
[pm2]: https://developers.google.com/google-ads/api/performance-max/create-campaign
[pm3]: https://developers.google.com/google-ads/api/performance-max/asset-requirements
[pm4]: https://developers.google.com/google-ads/api/performance-max/asset-groups
[pm5]: https://developers.google.com/google-ads/api/performance-max/structure-requests
[pm6]: https://developers.google.com/google-ads/api/performance-max/assets
[pm7]: https://developers.google.com/google-ads/api/performance-max/asset-group-signals
[pm8]: https://developers.google.com/google-ads/api/performance-max/listing-groups
[pm9]: https://developers.google.com/google-ads/api/performance-max/retail
[pm10]: https://developers.google.com/google-ads/api/performance-max/create-campaign-criteria
[pm12]: https://developers.google.com/google-ads/api/docs/assets/asset-automation-settings
[pm13]: https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign
[pm14]: https://raw.githubusercontent.com/googleapis/googleapis/master/google/ads/googleads/v25/resources/campaign.proto
[pm15]: https://developers.google.com/google-ads/api/reference/rpc/v25/AssetAutomationTypeEnum.AssetAutomationType
[pm16]: https://developers.google.com/google-ads/api/reference/rpc/v25/AssetAutomationStatusEnum.AssetAutomationStatus
[pm17]: https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.AssetAutomationSetting
[pm18]: https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.BrandGuidelines
[pm19]: https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.TextGuidelines
[pm20]: https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.MessagingRestriction
[pm21]: https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.PmaxCampaignSettings
[pm22]: https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.PmaxCampaignSettings.BrandTargetingOverrides
[pm23]: https://developers.google.com/google-ads/api/diff-tool/v22/versus-v21/diffs/resources/campaign
[pm24]: https://developers.google.com/google-ads/api/reference/rpc/v25/AssetGroup
[pm25]: https://raw.githubusercontent.com/googleapis/googleapis/master/google/ads/googleads/v25/resources/asset_group.proto
[pm26]: https://raw.githubusercontent.com/googleapis/googleapis/master/google/ads/googleads/v25/enums/asset_group_status.proto
[pm27]: https://developers.google.com/google-ads/api/reference/rpc/v25/AssetGroupErrorEnum.AssetGroupError
[pm28]: https://developers.google.com/google-ads/api/reference/rpc/v25/AssetGroupAsset
[pm29]: https://developers.google.com/google-ads/api/reference/rpc/v25/AssetGroupSignal
[pm30]: https://developers.google.com/google-ads/api/reference/rpc/v25/SearchThemeInfo
[pm31]: https://raw.githubusercontent.com/googleapis/googleapis/master/google/ads/googleads/v25/common/criteria.proto
[pm32]: https://developers.google.com/google-ads/api/reference/rpc/v25/AssetGroupListingGroupFilter
[pm33]: https://developers.google.com/google-ads/api/reference/rpc/v25/ListingGroupFilterTypeEnum.ListingGroupFilterType
[pm34]: https://developers.google.com/google-ads/api/reference/rpc/v25/ListingGroupFilterListingSourceEnum.ListingGroupFilterListingSource
[pm35]: https://developers.google.com/google-ads/api/reference/rpc/v25/ListingGroupFilterDimension
[pm36]: https://developers.google.com/google-ads/api/docs/best-practices/system-limits
[pm37]: https://raw.githubusercontent.com/googleads/google-ads-python/main/examples/shopping_ads/add_performance_max_retail_campaign.py
[pm38]: https://raw.githubusercontent.com/googleads/google-ads-python/main/examples/advanced_operations/add_performance_max_campaign.py
[pm39]: https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignCriterion
[pm40]: https://developers.google.com/google-ads/api/reference/rpc/v25/BrandListInfo
[pm41]: https://developers.google.com/google-ads/api/reference/rpc/v25/SharedSetTypeEnum.SharedSetType
[pm42]: https://developers.google.com/google-ads/api/reference/rpc/v25/SharedCriterion
[pm43]: https://developers.google.com/google-ads/api/reference/rpc/v25/BrandSuggestionService
[pm44]: https://developers.google.com/google-ads/api/reference/rpc/v25/CustomerNegativeCriterion
[pm45]: https://developers.google.com/google-ads/api/docs/targeting/shared-sets
[pm47]: https://support.google.com/google-ads/answer/14528373
[pm48]: https://support.google.com/google-ads/answer/14530211
[pm49]: https://support.google.com/google-ads/answer/14528532
[pm50]: https://support.google.com/google-ads/answer/15864742
[pm51]: https://support.google.com/google-ads/answer/14767319
[pm52]: https://support.google.com/google-ads/answer/11396330
[pm53]: https://developers.google.com/google-ads/api/docs/release-notes
[pm54]: https://developers.google.com/google-ads/api/docs/archived-release-notes

## 7. Conversion goals

**Conversion actions.** A conversion action is created with `ConversionActionService` and needs only `name` (unique in the conversion account, or `DUPLICATE_NAME`) and `type` (immutable) ([A1], [A4]). The types that can be created through the API are `WEBPAGE`, `AD_CALL`, `WEBSITE_CALL`, `UPLOAD_CLICKS`, `UPLOAD_CALLS`, `GOOGLE_PLAY_DOWNLOAD` and `GOOGLE_PLAY_IN_APP_PURCHASE` ([A5]). GA4, Firebase and third-party app conversions cannot be created: they appear with status `HIDDEN` and are imported by updating the status to `ENABLED`, after which only `status`, `primary_for_goal`, `category`, `name` and `value_settings` can change ([A6]). Store sales types cannot be created. The enum marks `WEBPAGE_CODELESS`, `GOOGLE_HOSTED`, `LEAD_FORM_SUBMIT`, `STORE_VISITS`, `STORE_SALES`, the Floodlight types, `SEARCH_ADS_360`, two Android types and the four `SMART_CAMPAIGN_*` types as read only ([A2]). `CLICK_TO_CALL` is neither read only nor in the creatable list **(unconfirmed)**. `UploadClickConversions` requests fail after 15 June 2026 for customers with no recent uploads, and Google points new integrations at the Data Manager API ([A5]).

**Goals.** Goals are grouped by `category` plus `origin`. Adding a conversion action creates a `CustomerConversionGoal` for its pair if none exists, and a `CampaignConversionGoal` for each campaign ([A21]). Google-managed goal objects "only support update operations; you cannot create or remove those objects"; `CustomConversionGoal` is the exception ([A21]). On v25, `CustomerConversionGoalOperation`, `CampaignConversionGoalOperation` and `ConversionGoalCampaignConfigOperation` offer only `update` with `update_mask`, and `CustomConversionGoalOperation` offers `create`, `update` and `remove` ([A12], [A14], [A16], [A19]). App campaigns use `Campaign.selective_optimization` instead of campaign goals ([A21]).

**Inside the atomic request.** `MutateOperation` carries `campaign_conversion_goal_operation`, `conversion_goal_campaign_config_operation`, `customer_conversion_goal_operation`, `custom_conversion_goal_operation` and `conversion_action_operation`, but **not** `goal_operation` or `campaign_goal_config_operation` ([A26]). Google's own Performance Max sample sends `campaign_conversion_goal_operation` updates in the same Mutate as the new campaign, using the temporary campaign id in the resource name `customers/{cid}/campaignConversionGoals/{TEMP_CAMPAIGN_ID}~{category}~{origin}` and placing them after the campaign create ([A24]). The resource is not tied to one channel, so the same works for Search. `CampaignConversionGoalOperation` requires `partial_failure` false ([A25]). Doing the same for `ConversionGoalCampaignConfig` or a new `CustomConversionGoal` with temporary ids is **(unconfirmed)**.

**Customer acquisition (lifecycle) goals changed in v25.** `CustomerLifecycleGoal`, `CampaignLifecycleGoal`, their services and settings were removed in v25 (22 July 2026). The release notes say: "Use `Goal.new_customer_acquisition_goal_settings` and `CampaignGoalConfig.campaign_new_customer_acquisition_settings` instead" ([A39]); the v25 pages for the old resources return 404 ([A45]). In v24 the modes were `TARGET_ALL_EQUALLY` (default), `BID_HIGHER_FOR_NEW_CUSTOMER` and `TARGET_NEW_CUSTOMER` ([A41], [A42], [A43]). `Goal` and `CampaignGoalConfig` already existed in v23 and v24 with retention settings only ([A44]); the v22 notes added customer retention goals under "Unified goals", so v22 is the likely first version **(unconfirmed)** ([A40]). `Goal` and `CampaignGoalConfig` are mutated only through `GoalService.MutateGoals` (`create`, `update`) and `CampaignGoalConfigService.MutateCampaignGoalConfigs` (`create`, `update`, `remove`), not through `GoogleAdsService.Mutate`, so they need a second call once the campaign has a real id ([A26], [A28], [A29], [A31], [A32]). Our reading of the guide's wording maps the old modes to the new ones as: `TARGET_ALL_EQUALLY` becomes `TARGET_ALL` without a value adjustment, `BID_HIGHER_FOR_NEW_CUSTOMER` becomes `TARGET_ALL` with value adjustments, and `TARGET_NEW_CUSTOMER` becomes `TARGET_SPECIFIC` ([A38]).

| Setting | Resource and field path | Values | Level | Campaign types | Source | PPCWay sends today |
|---|---|---|---|---|---|---|
| Conversion action name | `conversion_action.name` | String, required on create, unique per conversion account (`DUPLICATE_NAME`) | Account | All | [A1], [A4] | No |
| Conversion action type | `conversion_action.type` (immutable) | Creatable: `WEBPAGE`, `AD_CALL`, `WEBSITE_CALL`, `UPLOAD_CLICKS`, `UPLOAD_CALLS`, `GOOGLE_PLAY_DOWNLOAD`, `GOOGLE_PLAY_IN_APP_PURCHASE`. Import only (`HIDDEN` to `ENABLED`): GA4, Firebase, third-party app. Read only: `GOOGLE_HOSTED`, `WEBPAGE_CODELESS`, `LEAD_FORM_SUBMIT`, `STORE_VISITS`, `STORE_SALES`, `SMART_CAMPAIGN_*`, `FLOODLIGHT_*`, `SEARCH_ADS_360` | Account | All | [A2], [A5], [A6] | No |
| Category | `conversion_action.category` | `DEFAULT` (default), `PAGE_VIEW`, `PURCHASE`, `SIGNUP`, `DOWNLOAD`, `ADD_TO_CART`, `BEGIN_CHECKOUT`, `SUBSCRIBE_PAID`, `PHONE_CALL_LEAD`, `IMPORTED_LEAD`, `SUBMIT_LEAD_FORM`, `BOOK_APPOINTMENT`, `REQUEST_QUOTE`, `GET_DIRECTIONS`, `OUTBOUND_CLICK`, `CONTACT`, `ENGAGEMENT`, `STORE_VISIT`, `STORE_SALE`, `QUALIFIED_LEAD`, `CONVERTED_LEAD`, `YOUTUBE_FOLLOW_ON_VIEWS`, `IN_APP_AD_REVENUE`. `DOWNLOAD` only with `GOOGLE_PLAY_DOWNLOAD` | Account | All | [A3], [A4], [A6] | No |
| Status | `conversion_action.status` | `ENABLED` (default), `HIDDEN`, `REMOVED` | Account | All | [A4], [A9] | No |
| Primary (biddable) | `conversion_action.primary_for_goal` | bool, default true. False makes it non-biddable everywhere except through custom goals. `include_in_conversions_metric` is read only (`FieldError.IMMUTABLE_FIELD`) | Account | All | [A1], [A4] | No |
| Counting | `conversion_action.counting_type` | `MANY_PER_CLICK` (default), `ONE_PER_CLICK` | Account | All | [A1], [A4] | No |
| Value | `conversion_action.value_settings.{default_value, default_currency_code, always_use_default_value}` | `always_use_default_value` must be true for `AD_CALL` and `WEBSITE_CALL` (`INVALID_VALUE`) | Account | All | [A4], [A7] | No |
| Click-through window | `conversion_action.click_through_lookback_window_days` | 1 to 90 days; 1 to 60 for `AD_CALL` and `WEBSITE_CALL` | Account | All | [A1], [A4] | No |
| View-through window | `conversion_action.view_through_lookback_window_days` | 1 to 30 days; must be unset for call types (`VALUE_MUST_BE_UNSET`) | Account | All | [A1], [A4] | No |
| Attribution | `conversion_action.attribution_model_settings.attribution_model` | `GOOGLE_SEARCH_ATTRIBUTION_DATA_DRIVEN` (default), `GOOGLE_ADS_LAST_CLICK`. Rule-based models fail with `CANNOT_SET_RULE_BASED_ATTRIBUTION_MODELS` | Account | All | [A4], [A8] | No |
| Minimum call length | `conversion_action.phone_call_duration_seconds` | 0 to 10,000 seconds; call types only | Account | All | [A1], [A4] | No |
| Origin | `conversion_action.origin` (output only) | `WEBSITE`, `GOOGLE_HOSTED`, `APP`, `CALL_FROM_ADS`, `STORE`, `YOUTUBE_HOSTED`, `LOCAL_SERVICES_ADS` | Account | All | [A1], [A10] | Not applicable |
| Account default goal | `customer_conversion_goal.biddable`; resource `customers/{cid}/customerConversionGoals/{category}~{origin}` | bool; update only; created by the system | Account | All except App | [A11], [A12], [A21] | No |
| Campaign goal override | `campaign_conversion_goal.biddable` (with `campaign`, `category`, `origin`); resource `customers/{cid}/campaignConversionGoals/{campaign_id}~{category}~{origin}`; sent as `campaign_conversion_goal_operation` | bool; update only; unset inherits the account default. Works with a temporary campaign id in the same Mutate (Google sample); needs `partial_failure` false | Campaign | All except App | [A13], [A14], [A21], [A24], [A25], [A26] | No |
| Goal source | `conversion_goal_campaign_config.goal_config_level`; resource `customers/{cid}/conversionGoalCampaignConfigs/{campaign_id}` | `CUSTOMER`, `CAMPAIGN`; update only. Changing campaign goals sets `CAMPAIGN`; setting `CUSTOMER` resyncs to account goals and drops a custom goal | Campaign | All except App | [A15], [A16], [A17], [A21], [A22] | No |
| Custom goal on a campaign | `conversion_goal_campaign_config.custom_conversion_goal` (update mask `custom_conversion_goal`) | Resource name of a `CustomConversionGoal`. In the creation Mutate with temporary ids **(unconfirmed)** | Campaign | All except App **(per-type list unconfirmed)** | [A15], [A22] | No |
| Custom goal | `custom_conversion_goal.{name, conversion_actions[], status}` | Status `ENABLED` or `REMOVED`; create, update, remove; ignores `primary_for_goal` | Account | All except App **(unconfirmed)** | [A4], [A18], [A19], [A20], [A21] | No |
| New customer acquisition, account | `goal.new_customer_acquisition_goal_settings.value_settings` (`goal_type = NEW_CUSTOMER_ACQUISITION`, output only), through `GoalService.MutateGoals` | `value_adjustment`: `additional_value` (the multiplier is not supported for this goal); `high_lifetime_value_adjustment`: `additional_high_lifetime_value` (multiplier "not supported yet"). At most one Goal per type. Needs audiences segmented with `UserListCustomerType`. Not in `MutateOperation` | Account | **(unconfirmed in the API docs)** | [A26], [A27], [A28], [A29], [A35], [A36], [A37], [A38] | No |
| New customer acquisition, campaign | `campaign_goal_config.campaign_new_customer_acquisition_settings.{target_option, value_settings_override}` with `goal` and `campaign` (immutable), through `CampaignGoalConfigService.MutateCampaignGoalConfigs`; resource `customers/{cid}/campaignGoalConfigs/{campaign_id}~{goal_id}` | `TARGET_ALL` (default: new and existing customers, bidding higher for new) or `TARGET_SPECIFIC` (new customers only). Separate call after the campaign exists | Campaign | **(unconfirmed in the API docs)** | [A26], [A30], [A31], [A32], [A33], [A34], [A38] | No |
| Retention and loyalty goals | `goal.retention_goal_settings`, `goal.loyalty_retention_goal_settings`, `campaign_goal_config.campaign_retention_settings`, `.campaign_loyalty_retention_settings` | `CUSTOMER_RETENTION` needs Performance Max and a Customer Match list (its `TARGET_SPECIFIC` is allowlisted). `LOYALTY_RETENTION` is new in v25 | Account and campaign | PERFORMANCE_MAX | [A27], [A30], [A36], [A38], [A39] | No |
| Legacy lifecycle goals | `CustomerLifecycleGoal`, `CampaignLifecycleGoal.customer_acquisition_goal_settings`, `CampaignLifecycleGoalService.ConfigureCampaignLifecycleGoals` | **Removed in v25** | Not applicable | Not applicable | [A39], [A41], [A42], [A43], [A45] | No |

### 7.1 How a campaign picks its goals at creation

A new campaign takes the account defaults: every `CustomerConversionGoal` with `biddable` true is biddable for it, and the campaign keeps following account-level changes until its own goals or a custom goal are set ([A21]). If the account has no conversion actions, there are no goals, and conversion-based bidding has nothing to aim at (our inference; this is the PDFezy problem noted in PPCWay's coverage page). To choose goals inside PPCWay's single atomic request:

1. Before the Mutate, read the account's goal pairs: `SELECT customer_conversion_goal.category, customer_conversion_goal.origin, customer_conversion_goal.biddable FROM customer_conversion_goal` (the same step as Google's sample, [A24]).
2. In the same `GoogleAdsService.Mutate`, after the campaign create (for example `customers/{cid}/campaigns/-2`), add one `campaignConversionGoalOperation` per pair: `{"update": {"resourceName": "customers/{cid}/campaignConversionGoals/-2~PURCHASE~WEBSITE", "biddable": true}, "updateMask": "biddable"}`. Keep `partialFailure` false ([A14], [A24], [A25]).
3. The campaign then moves to `goal_config_level = CAMPAIGN`, and later account-default changes no longer reach it ([A21], [A22]).
4. For a custom goal instead, create it with `custom_conversion_goal_operation.create {name, conversion_actions[], status: ENABLED}`, then update `conversionGoalCampaignConfigs/{campaign_id}` with `custom_conversion_goal` and `update_mask: custom_conversion_goal` ([A19], [A22]). Whether both work with temporary ids in the creation Mutate is **(unconfirmed)**; the safe path is a second Mutate after launch.
5. To go back to account defaults, update `goal_config_level` to `CUSTOMER` ([A22]).
6. New-customer bidding always needs separate calls after the campaign exists: once per account, `GoalService.MutateGoals` creating a `Goal` with `new_customer_acquisition_goal_settings`; then `CampaignGoalConfigService.MutateCampaignGoalConfigs` creating `{campaign, goal, campaign_new_customer_acquisition_settings: {target_option}}` ([A26], [A28], [A31], [A38]).

[A1]: https://developers.google.com/google-ads/api/reference/rpc/v25/ConversionAction
[A2]: https://developers.google.com/google-ads/api/reference/rpc/v25/ConversionActionTypeEnum.ConversionActionType
[A3]: https://developers.google.com/google-ads/api/reference/rpc/v25/ConversionActionCategoryEnum.ConversionActionCategory
[A4]: https://developers.google.com/google-ads/api/docs/conversions/create-conversion-actions
[A5]: https://developers.google.com/google-ads/api/docs/conversions/overview
[A6]: https://developers.google.com/google-ads/api/docs/conversions/categories
[A7]: https://developers.google.com/google-ads/api/reference/rpc/v25/ConversionAction.ValueSettings
[A8]: https://developers.google.com/google-ads/api/reference/rpc/v25/ConversionAction.AttributionModelSettings
[A9]: https://developers.google.com/google-ads/api/reference/rpc/v25/ConversionActionStatusEnum.ConversionActionStatus
[A10]: https://developers.google.com/google-ads/api/reference/rpc/v25/ConversionOriginEnum.ConversionOrigin
[A11]: https://developers.google.com/google-ads/api/reference/rpc/v25/CustomerConversionGoal
[A12]: https://developers.google.com/google-ads/api/reference/rpc/v25/CustomerConversionGoalOperation
[A13]: https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignConversionGoal
[A14]: https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignConversionGoalOperation
[A15]: https://developers.google.com/google-ads/api/reference/rpc/v25/ConversionGoalCampaignConfig
[A16]: https://developers.google.com/google-ads/api/reference/rpc/v25/ConversionGoalCampaignConfigOperation
[A17]: https://developers.google.com/google-ads/api/reference/rpc/v25/GoalConfigLevelEnum.GoalConfigLevel
[A18]: https://developers.google.com/google-ads/api/reference/rpc/v25/CustomConversionGoal
[A19]: https://developers.google.com/google-ads/api/reference/rpc/v25/CustomConversionGoalOperation
[A20]: https://developers.google.com/google-ads/api/reference/rpc/v25/CustomConversionGoalStatusEnum.CustomConversionGoalStatus
[A21]: https://developers.google.com/google-ads/api/docs/conversions/goals/overview
[A22]: https://developers.google.com/google-ads/api/docs/conversions/goals/campaign-goals
[A24]: https://developers.google.com/google-ads/api/samples/add-performance-max-retail-campaign
[A25]: https://developers.google.com/google-ads/scripts/docs/campaigns/performance-max/optional-components
[A26]: https://developers.google.com/google-ads/api/reference/rpc/v25/MutateOperation
[A27]: https://developers.google.com/google-ads/api/reference/rpc/v25/Goal
[A28]: https://developers.google.com/google-ads/api/reference/rpc/v25/GoalOperation
[A29]: https://developers.google.com/google-ads/api/reference/rpc/v25/GoalService
[A30]: https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignGoalConfig
[A31]: https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignGoalConfigOperation
[A32]: https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignGoalConfigService
[A33]: https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignGoalSettings.CampaignNewCustomerAcquisitionGoalSettings
[A34]: https://developers.google.com/google-ads/api/reference/rpc/v25/CustomerLifecycleOptimizationModeEnum.CustomerLifecycleOptimizationMode
[A35]: https://developers.google.com/google-ads/api/reference/rpc/v25/CustomerLifecycleOptimizationValueSettings
[A36]: https://developers.google.com/google-ads/api/reference/rpc/v25/GoalTypeEnum.GoalType
[A37]: https://developers.google.com/google-ads/api/reference/rpc/v25/GoalSetting.NewCustomerAcquisitionGoal
[A38]: https://developers.google.com/google-ads/api/docs/conversions/goals/lifecycle-goals
[A39]: https://developers.google.com/google-ads/api/docs/release-notes
[A40]: https://developers.google.com/google-ads/api/docs/archived-release-notes
[A41]: https://developers.google.com/google-ads/api/reference/rpc/v24/CampaignLifecycleGoal
[A42]: https://developers.google.com/google-ads/api/reference/rpc/v24/CampaignLifecycleGoalService
[A43]: https://developers.google.com/google-ads/api/reference/rpc/v24/CustomerAcquisitionOptimizationModeEnum.CustomerAcquisitionOptimizationMode
[A44]: https://developers.google.com/google-ads/api/reference/rpc/v24/CampaignGoalConfig
[A45]: https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignLifecycleGoal

## 8. Helper services the creation flow can use

**Access level.** Explorer access cannot use the planning services: `KeywordPlanService`, `KeywordPlanIdeaService`, the `KeywordPlan*` services, `AudienceInsightsService` and `ReachPlanService` need Basic or Standard access ([B26]). Since developer tokens were sunset on 9 September 2026, the access level belongs to the Google Cloud project (section 10.1).

**Forecasts.** Saved-plan forecast methods were removed from `KeywordPlanService` in v14; in v25 it has only `MutateKeywordPlans` ([B14], [B15]). The replacement, `KeywordPlanIdeaService.GenerateKeywordForecastMetrics`, needs no saved plan, but v24 cut it down: no negative keywords, no conversion rate input, no network choice, no per-keyword bids, and no impressions or CTR in the answer ([B12], [B32]).

| Service and method | Inputs | Returns | Limits and access | Usable before the campaign exists | Source | PPCWay uses today |
|---|---|---|---|---|---|---|
| `KeywordPlanIdeaService.GenerateKeywordIdeas` | `customer_id`; seed oneof `keyword_seed`, `url_seed`, `site_seed`, `keyword_and_url_seed`; `language`, `geo_target_constants[]`, `include_adult_keywords` (default false), `keyword_plan_network` (default Google Search and Partners), `keyword_annotation[]`, `aggregate_metrics`, `historical_metrics_options` (`year_month_range` up to 4 years back, default 12 months; `include_average_cpc`), `page_size`, `page_token` | `results[]`: `text`, `close_variants[]`, `keyword_idea_metrics` (`avg_monthly_searches`, `monthly_search_volumes[]`, `competition` LOW, MEDIUM or HIGH, `competition_index` 0 to 100, `low_top_of_page_bid_micros` at the 20th percentile, `high_top_of_page_bid_micros` at the 80th, `average_cpc_micros`), `keyword_annotations`; plus `aggregate_metric_results`, `next_page_token`, `total_size` | 1 to 20 seed keywords; at most 10 geos; up to 10,000 results per page; a site seed yields up to 250,000 ideas; 1 request per second per customer; Basic or Standard access | Yes | [B1], [B2], [B3], [B4], [B5], [B6], [B26], [B27] | Yes |
| `KeywordPlanIdeaService.GenerateKeywordHistoricalMetrics` | `customer_id`, `keywords[]`, `language`, `geo_target_constants[]`, `include_adult_keywords`, `keyword_plan_network`, `aggregate_metrics`, `historical_metrics_options` | Per keyword: `text`, `close_variants`, `keyword_metrics` (as above) | At most 10,000 keywords; near-duplicates may be dropped; at most 10 geos; 1 request per second per customer | Yes | [B7], [B13], [B27] | No |
| `KeywordPlanIdeaService.GenerateKeywordForecastMetrics` | `customer_id`, `currency_code`, `forecast_period`, and `campaign` (`CampaignToForecast`, required) with `language_constants[]`, `geo_target_constants[]`, `ad_groups[].keywords[]` (at least 1), and `bidding_strategy` as one of `manual_cpc_bidding_strategy` (`max_cpc_bid_micros`, `daily_budget_micros`), `maximize_clicks_bidding_strategy` (`max_cpc_bid_ceiling_micros`, `daily_target_spend_micros`) or `maximize_conversions_bidding_strategy` (`daily_target_spend_micros`) | Campaign-level `KeywordForecastMetrics`: `cost_micros`; `clicks` and `average_cpc_micros` only with manual CPC or maximize clicks; `conversions` and `average_cpa_micros` only with maximize conversions. No impressions, no per-keyword forecast | Period must start in the future and end within a year (default next Sunday to the following Saturday); 1 request per second per customer; Basic or Standard access | Yes (inline campaign) | [B9], [B10], [B11], [B12], [B27] | No |
| `KeywordPlanIdeaService.GenerateAdGroupThemes` | `customer_id`, `keywords[]`, `ad_groups[]` (existing ad group resource names) | Keywords grouped into those ad groups, with suggested match types | 2 requests per second per customer | No (needs existing ad groups) | [B8], [B13], [B27] | No |
| `KeywordPlanService.MutateKeywordPlans` and the `KeywordPlan*` services | `keyword_plan.name` (required), `forecast_period` | A saved plan only; its forecast methods were removed in v14 | Explorer access blocked | Yes, but not needed | [B14], [B15], [B26] | No |
| `RecommendationService.GenerateRecommendations` | `customer_id`, `advertising_channel_type` (`SEARCH` or `PERFORMANCE_MAX`), `recommendation_types[]`, `seed_info` (`keyword_seeds[]`, `url_seed`), `ad_group_info[]` (`ad_group_type`, `keywords[]`; one ad group), `bidding_info` (`bidding_strategy_type`, plus one of `target_cpa_micros`, `target_roas`, `target_impression_share_info`), `budget_info.current_budget`, `conversion_tracking_status`, `campaign_sitelink_count`, `campaign_image_asset_count`, `campaign_call_asset_count`, `country_codes[]`, `language_codes[]`, `positive_locations_ids[]`, `negative_locations_ids[]`, `asset_group_info[]` (`final_url`, `headline[]`, `description[]`), `target_partner_search_network`, `target_content_network`, `merchant_center_account_id` (Performance Max retail), `is_new_customer` (accounts with no campaigns; from v23) | A list of `Recommendation` objects; nothing is applied, the app copies accepted values into its own create request. A type missing its inputs is simply left out, with no error | Not in the Explorer restriction list; quota **(unconfirmed)** | **Yes, built for campaign construction** | [B16], [B17], [B26], [B32] | No |
| `RecommendationService.ApplyRecommendation`, `DismissRecommendation` | `customer_id`, `operations[]` (`resource_name`, optional `apply_parameters`) | Applied or dismissed results | Up to 100 operations per request; one type per request unless `partial_failure` is true (`DIFFERENT_TYPES_NOT_SUPPORTED`) | No (existing campaigns) | [B17], [B18] | No |
| `BrandSuggestionService.SuggestBrands` | `customer_id`, `brand_prefix` (required), `selected_brands[]` (ids to leave out) | `BrandSuggestion`: `id`, `name`, `urls[]`, `state` (`ENABLED`, `UNVERIFIED`, `APPROVED`, `REJECTED`, `CANCELLED`, `DEPRECATED`) | No limits or allowlist stated. Feeds a `BRANDS` shared set used through `brand_list` criteria (sections 2.5 and 3.6) | Yes | [B19], [B20] | No |
| `GeoTargetConstantService.SuggestGeoTargetConstants` | `locale` (ISO 639-1, falls back to `en`), `country_code`, and one of `location_names` or `geo_targets` | `GeoTargetConstantSuggestion`: `geo_target_constant` (`id`, `name`, `canonical_name`, `country_code`, `target_type`, `status` `ENABLED` or `REMOVAL_PLANNED`, `parent_geo_target`), `geo_target_constant_parents[]`, `locale`, `reach` (rounded to the nearest 100), `search_term` | At most 25 location names; limit on `geo_targets` **(unconfirmed)** | Yes | [B21] | Yes |
| `ReachPlanService`: `ListPlannableLocations`, `ListPlannableProducts`, `GenerateReachForecast`, `GenerateConversionRates`, `ListPlannableUserLists`, `ListPlannableUserInterests` | Forecast: `customer_id`, `campaign_duration` (required), `planned_products[]` (required, at most 15), `targeting`, `currency_code`, `cookie_frequency_cap_setting`, `min_effective_frequency` (1 to 10) or `effective_frequency_limit`, `forecast_metric_options`, `customer_reach_group` | YouTube reach, impression and on-target audience forecasts (exact field names **(unconfirmed)**); Demand Gen conversion-rate suggestions | Allowlisted accounts only, with an approved Cloud project. v25 removed `plannable_location_id` and `cookie_frequency_cap` | Yes (video planning, not Search) | [B22], [B26], [B32] | No |
| `AudienceInsightsService`: `GenerateInsightsFinderReport`, `ListAudienceInsightsAttributes`, `GenerateAudienceCompositionInsights`, `GenerateSuggestedTargetingInsights`, `GenerateAudienceOverlapInsights`, `GenerateTargetingSuggestionMetrics`, `ListInsightsEligibleDates`, `GenerateAudienceDefinition` (generative, from v23) | For `GenerateAudienceDefinition`: `customer_id`, `audience_description` (free text), `customer_insights_group`, `insights_application_info` | Audience attribute and composition insights for YouTube and Demand Gen planning | "Accessible to allowlisted customers only"; about 200 requests a day per customer for composition and suggested targeting; Explorer blocked | Yes (not Search keyword planning) | [B23], [B26], [B27], [B32] | No |
| `ShareablePreviewService.GenerateShareablePreviews` | `customer_id`, `operation.shareable_previews[]`, each with `preview_type` (`UI_PREVIEW` or `YOUTUBE_LIVE_PREVIEW`) and one of `asset_group` (existing) or `ad_group_ad` (YouTube Live only) | `ShareablePreviewResult`: identifier, `expiration_date_time`, and `ui_preview_result.shareable_preview_url` or `youtube_live_preview_result` | No partial failure since v24; a `TOO_MANY_RESOURCES_IN_REQUEST` cap exists **(value unconfirmed)**. Performance Max asset groups and YouTube ads only; **no Search ad previews** | No (needs a saved asset group or ad) | [B24], [B32] | No |
| `AssetGenerationService.GenerateText` | `customer_id`, `asset_field_types[]` (`HEADLINE`, `LONG_HEADLINE`, `DESCRIPTION`), context as one of `advertising_channel_type` (`SEARCH`, `PERFORMANCE_MAX`, `DISPLAY`, `DEMAND_GEN`) or `existing_generation_context` (`existing_asset_group` or `existing_ad_group_ad`), `final_url` (required without a context), `freeform_prompt` (1 to 1,500 characters), `keywords[]` | `generated_text[]` (`text`, `asset_field_type`) | Arrived in v22 as a closed beta "initially available only to a limited set of closed beta participants"; no general availability note through v26.2, so treat as allowlisted **(v25 status unconfirmed)**. Errors include `TOO_MANY_KEYWORDS`, `FINAL_URL_UNAVAILABLE`, `UNSUPPORTED_FIELD_TYPE_FOR_CAMPAIGN_TYPE` and prompt policy errors | Yes (channel type plus final URL) | [B25], [B32] | No |
| `AssetGenerationService.GenerateImages` | `customer_id`, `asset_field_types[]` (`MARKETING_IMAGE`, `SQUARE_MARKETING_IMAGE`, `PORTRAIT_MARKETING_IMAGE`, `TALL_PORTRAIT_MARKETING_IMAGE`), the same context oneof, and one of `final_url_generation`, `freeform_generation`, `product_recontext_generation` | `generated_images[]` (`image_temporary_url`, `asset_field_type`); the image must then be uploaded as an asset (our inference) | Same beta status; output filtered for children, specific people and brand content | Yes | [B25], [B32] | No |
| `SmartCampaignSuggestService`: `SuggestKeywordThemes`, `SuggestSmartCampaignAd`, `SuggestSmartCampaignBudgetOptions` | `suggestion_info` (`final_url`, `language_code`, `keyword_themes`; optional `business_setting`, `geo_target`) | Keyword themes, ad text and budget options for Smart campaigns | Smart campaigns can no longer be created (section 9), so of limited use | Yes | [B28] | No |
| `KeywordThemeConstantService.SuggestKeywordThemeConstants` | Text query, country and language **(fields unconfirmed)** | Smart campaign keyword theme constants | Smart campaigns only | Yes | [B28] | No |
| `BenchmarksService`, `ContentCreatorInsightsService` | Products, locations, dates; topics, channels | YouTube benchmarks; creator and trend insights | Allowlisted only; Benchmarks added in v23 | Yes | [B29], [B32] | No |
| `IncentiveService.FetchIncentive`, `ApplyIncentive` | Fetch: `language_code`, `country_code` (default US), `email`, `incentive_type`. Apply: `customer_id`, `selected_incentive_id`, `country_code` (must match billing) | Sign-up promotional offers (from v23) | No allowlist stated | Yes (account onboarding) | [B30], [B32] | No |
| `TravelAssetSuggestionService.SuggestTravelAssets` | Travel and hotel inputs | Travel asset suggestions | Travel only, closed allowlist | Yes | [B31] | No |

### 8.1 Recommendation types GenerateRecommendations supports in v25

The channel input accepts only `SEARCH` or `PERFORMANCE_MAX` ([B16], [B17]).

- **`CAMPAIGN_BUDGET`**, both channels. Both need `asset_group_info` with `final_url` and `bidding_info.bidding_strategy_type`. Search also needs `country_codes`, `language_codes`, positive or negative location ids and `ad_group_info.keywords`, plus `target_impression_share_info` under target impression share. Optional: `budget_info`, `is_new_customer`, asset counts, network flags; on Performance Max, `merchant_center_account_id` gives retail suggestions.
- **`KEYWORD`**: needs `seed_info`; `ad_group_info` optional. The docs do not restrict the channel; in practice Search only **(unconfirmed)**.
- **`SITELINK_ASSET`**: needs `campaign_sitelink_count`. The answer has no content; it only signals "add at least one sitelink" **(channel unconfirmed)**.
- **Bidding**: `MAXIMIZE_CLICKS_OPT_IN`, `MAXIMIZE_CONVERSIONS_OPT_IN`, `MAXIMIZE_CONVERSION_VALUE_OPT_IN`, `SET_TARGET_CPA`, `SET_TARGET_ROAS`, `TARGET_CPA_OPT_IN`, `TARGET_ROAS_OPT_IN`. Each needs `conversion_tracking_status` and `bidding_info`; per-type channel limits are not documented **(unconfirmed)**.
- **Not available for generation in v25**: `CALL_ASSET`, `CALLOUT_ASSET` and `RESPONSIVE_SEARCH_AD`. `campaign_call_asset_count` only feeds `CAMPAIGN_BUDGET`. An "optimize for new customers" recommendation arrived in v26.1, so it is not in v25 ([A39]).

[B1]: https://developers.google.com/google-ads/api/reference/rpc/v25/KeywordPlanIdeaService
[B2]: https://developers.google.com/google-ads/api/reference/rpc/v25/GenerateKeywordIdeasRequest
[B3]: https://developers.google.com/google-ads/api/reference/rpc/v25/KeywordSeed
[B4]: https://developers.google.com/google-ads/api/docs/keyword-planning/generate-keyword-ideas
[B5]: https://developers.google.com/google-ads/api/reference/rpc/v25/KeywordPlanHistoricalMetrics
[B6]: https://developers.google.com/google-ads/api/reference/rpc/v25/GenerateKeywordIdeaResponse
[B7]: https://developers.google.com/google-ads/api/reference/rpc/v25/GenerateKeywordHistoricalMetricsRequest
[B8]: https://developers.google.com/google-ads/api/reference/rpc/v25/GenerateAdGroupThemesRequest
[B9]: https://developers.google.com/google-ads/api/reference/rpc/v25/GenerateKeywordForecastMetricsRequest
[B10]: https://developers.google.com/google-ads/api/reference/rpc/v25/CampaignToForecast
[B11]: https://developers.google.com/google-ads/api/reference/rpc/v25/KeywordForecastMetrics
[B12]: https://developers.google.com/google-ads/api/docs/keyword-planning/generate-forecast-metrics
[B13]: https://developers.google.com/google-ads/api/docs/keyword-planning/overview
[B14]: https://developers.google.com/google-ads/api/reference/rpc/v25/KeywordPlanService
[B15]: https://groups.google.com/g/adwords-api/c/YbUX1YFwBqE
[B16]: https://developers.google.com/google-ads/api/reference/rpc/v25/GenerateRecommendationsRequest
[B17]: https://developers.google.com/google-ads/api/docs/recommendations
[B18]: https://developers.google.com/google-ads/api/reference/rpc/v25/RecommendationService
[B19]: https://developers.google.com/google-ads/api/reference/rpc/v25/SuggestBrandsRequest
[B20]: https://developers.google.com/google-ads/api/reference/rpc/v25/BrandListInfo
[B21]: https://developers.google.com/google-ads/api/reference/rpc/v25/SuggestGeoTargetConstantsRequest
[B22]: https://developers.google.com/google-ads/api/reference/rpc/v25/ReachPlanService
[B23]: https://developers.google.com/google-ads/api/reference/rpc/v25/AudienceInsightsService
[B24]: https://developers.google.com/google-ads/api/reference/rpc/v25/GenerateShareablePreviewsRequest
[B25]: https://developers.google.com/google-ads/api/reference/rpc/v25/AssetGenerationService
[B26]: https://developers.google.com/google-ads/api/docs/api-policy/access-levels
[B27]: https://developers.google.com/google-ads/api/docs/best-practices/quotas
[B28]: https://developers.google.com/google-ads/api/reference/rpc/v25/SmartCampaignSuggestService
[B29]: https://developers.google.com/google-ads/api/reference/rpc/v25/BenchmarksService
[B30]: https://developers.google.com/google-ads/api/reference/rpc/v25/IncentiveService
[B31]: https://developers.google.com/google-ads/api/reference/rpc/v25/TravelAssetSuggestionService
[B32]: https://developers.google.com/google-ads/api/docs/release-notes

## 9. Other campaign types

This section is at lower depth. In short: Demand Gen, Display, standard Shopping and App campaigns can be created through the API in v25. Video, Local Services and Smart campaigns cannot. Hotel is for allowlisted accounts only, and Travel has no creation guide.

| Campaign type | Channel type and sub-type | Creatable through the API in v25 | Minimum resources | Read-only, UI-only or allowlisted parts | Source |
|---|---|---|---|---|---|
| Demand Gen | `DEMAND_GEN`, sub-type unset | Yes | A budget that is not shared, either daily and at or above the Demand Gen minimum (5 USD or equivalent, enforced from 1 April 2026) or a total budget (`total_amount_micros`, `CUSTOM_PERIOD`) with start and end dates. A campaign with `maximize_conversions`, `maximize_conversion_value`, `target_cpa`, `target_roas`, `target_spend` or `target_cpc`, and `contains_eu_political_advertising`; optional `demand_gen_campaign_settings.upgraded_targeting` (default true, create only). Ad groups with no `type`, optional `demand_gen_ad_group_settings.channel_controls` (`channel_strategy` or `selected_channels`, default all channels). Image, logo and YouTube video assets. An `AdGroupAd` with `DemandGenMultiAssetAdInfo`, `DemandGenCarouselAdInfo`, `DemandGenVideoResponsiveAdInfo` (needs `business_name`; `videos` and `logo_images` required from v24) or `DemandGenProductAdInfo`. Google recommends one atomic Mutate with temporary ids. | Product feeds need `shopping_setting.merchant_id` (optional `feed_label`) and listing group criteria; no allowlist found. Campaigns migrated from Video Action or Display start `PAUSED`. The create guide still says "start_date and end_date", which are stale names in v25. | https://developers.google.com/google-ads/api/docs/demand-gen/overview, https://developers.google.com/google-ads/api/docs/demand-gen/create-campaign, https://developers.google.com/google-ads/api/docs/demand-gen/product-ads, https://developers.google.com/google-ads/api/docs/demand-gen/channel-controls, https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.DemandGenCampaignSettings, https://developers.google.com/google-ads/api/docs/deprecations |
| Display | `DISPLAY`, sub-type unset | Yes | Budget; campaign with a bidding strategy and `contains_eu_political_advertising`; ad group `DISPLAY_STANDARD`; image assets; an `AdGroupAd` with `final_urls` and `ResponsiveDisplayAdInfo`: `marketing_images` (at least 1, 1.91:1, minimum 600 by 314), `square_marketing_images` (at least 1, 1:1, minimum 300 by 300), `headlines` (1 to 5, 30 characters), `long_headline` (90), `descriptions` (1 to 5, 90), `business_name` (25). | `DISPLAY_SMART_CAMPAIGN` cannot be created. `DISPLAY_GMAIL_AD`, `DISPLAY_EXPRESS` and `DISPLAY_MOBILE_APP` are legacy, and whether they can be created is **(unconfirmed)**. There is no dedicated Display campaign guide; these facts come from the responsive display ad guide. | https://developers.google.com/google-ads/api/docs/campaigns/overview, https://developers.google.com/google-ads/api/docs/responsive-display-ads/create-responsive-display-ads, https://developers.google.com/google-ads/api/reference/rpc/v25/AdGroupTypeEnum.AdGroupType |
| Video | `VIDEO`; sub-types `VIDEO_ACTION`, `VIDEO_NON_SKIPPABLE`, `VIDEO_REACH_TARGET_FREQUENCY`, `VIDEO_SEQUENCE`, `YOUTUBE_AUDIO` | **No** | None. Google's guide says Video campaigns "cannot be created or mutated" through the API. Exceptions: `VideoResponsiveAdInfo` can be changed from v24 (and then needs `videos`, `business_name` and `logo_images`), and `experiment.video_experiment` exists from v24. | All Video campaigns are read-only through the API, for reporting. Use Demand Gen instead. Video Action creation was removed in April 2025 and existing campaigns were upgraded to Demand Gen by April 2026. `YOUTUBE_AUDIO` is read-only from v19.1. | https://developers.google.com/google-ads/api/docs/video/overview, https://support.google.com/google-ads/answer/15110871, https://developers.google.com/google-ads/api/docs/archived-release-notes |
| Shopping (standard) | `SHOPPING`, sub-type unset | Yes | A Merchant Center link first: `ProductLinkService.CreateProductLink` with `product_link.merchant_center.merchant_center_id` when admin on both, otherwise accept the invitation with `ProductLinkInvitationService.UpdateProductLinkInvitation`. Campaign with `shopping_setting.merchant_id` (required, immutable) and `campaign_priority` (0 to 2), optional `feed_label`, `enable_local`, and from v24.2 `ignore_brand_exclusion_in_shopping_ads`. Bidding `manual_cpc`, `target_spend`, `target_roas` or `maximize_conversion_value`. Ad group `SHOPPING_PRODUCT_ADS`, an `AdGroupAd` with `ShoppingProductAdInfo`, and a listing group tree with at least a root node. | `target_content_network = true` fails with `CANNOT_TARGET_CONTENT_NETWORK`. Comparison listing campaigns (`SHOPPING_COMPARISON_LISTING_ADS`) are for CSS-programme accounts only, manual CPC only. `SHOPPING_SMART_ADS` cannot be created. `listing_type = VEHICLES` needs v26. AI Max for Shopping is supported per `AiMaxSetting`; any allowlist is **(unconfirmed)**. | https://developers.google.com/google-ads/api/docs/shopping-ads/create-campaign, https://developers.google.com/google-ads/api/docs/shopping-ads/merchant-center, https://developers.google.com/google-ads/api/docs/shopping-ads/create-ad-group, https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.ShoppingSetting, https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.AiMaxSetting |
| App | `MULTI_CHANNEL`; sub-types `APP_CAMPAIGN`, `APP_CAMPAIGN_FOR_ENGAGEMENT`, `APP_CAMPAIGN_FOR_PRE_REGISTRATION` | Yes | A budget that is not shared. `app_campaign_setting.app_id` and `app_store` (both immutable) and `bidding_strategy_goal_type`. Campaign-level bidding only, no portfolio: `target_cpa`, `target_roas`, `maximize_conversions` or `maximize_conversion_value`. `selective_optimization.conversion_actions` for engagement, in-app action and target ROAS goals. Pre-registration needs `optimization_goal_setting` with `APP_PRE_REGISTRATION`. Ad groups with no type; engagement campaigns need a `user_list` criterion. `AdGroupAd` with `AppAdInfo`, `AppEngagementAdInfo` or `AppPreRegistrationAdInfo`. | Negative keywords only through a `CampaignSharedSet` (from v22). `view_through_conversion_optimization_enabled` from v24, Android `APP_CAMPAIGN` only. | https://developers.google.com/google-ads/api/docs/app-campaigns/create-campaign, https://developers.google.com/google-ads/api/docs/app-campaigns/create-ad-group, https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.AppCampaignSetting |
| Local Services | `LOCAL_SERVICES`, no sub-type | **No** | Not applicable. Existing campaigns allow updates to `status`, the budget `amount_micros`, bidding (`manual_cpa` through `local_services_campaign_settings.category_bids[]`, or `maximize_conversions`), and ad schedule, location and `local_service_id` criteria. | Create and remove are blocked. Ad groups, ads and other criteria can be neither read nor written. Local Services through Performance Max (`pmax_campaign_settings.local_services_enabled`) becomes creatable only in v26; in v25 it is output only. | https://developers.google.com/google-ads/api/docs/campaigns/local-service-campaigns, https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.LocalServicesCampaignSettings, https://developers.google.com/google-ads/api/docs/release-notes |
| Smart | `SMART` with `SMART_CAMPAIGN` | **No**, blocked in all versions since 23 September 2026 | Not applicable. Existing Smart campaigns can still be updated. | Creating one returns `SmartCampaignError.CREATION_FAILED` (v24 and later per Google's blog; v25 assumed the same, **(unconfirmed)**). `SmartCampaignSettingService.GeneratePMaxDraftCampaign` (v25.2) turns one into a Performance Max draft. | https://developers.google.com/ads/blog/posts/2026/06/changes-to-support-for-smart-campaigns, https://developers.google.com/google-ads/api/docs/smart-campaigns/overview, https://developers.google.com/google-ads/api/docs/deprecations, https://developers.google.com/google-ads/api/docs/release-notes |
| Hotel | `HOTEL`, no sub-type | Yes, **allowlisted accounts only** | Budget, campaign with `hotel_setting.hotel_center_id` and a bidding strategy, ad group `HOTEL_ADS`, a hotel ad, and hotel listing groups. | Feeds and prices live only in Hotel Center. | https://developers.google.com/google-ads/api/docs/hotel-ads/overview, https://developers.google.com/google-ads/api/docs/hotel-ads/create-campaign |
| Performance Max for travel goals | `PERFORMANCE_MAX`, sub-type unset | Yes | A Performance Max campaign with `hotel_property_asset_set` (immutable) pointing at the synced `HOTEL_PROPERTY` asset set, and an active Hotel Center link. | `TravelAssetSuggestionService` is a closed allowlist. Creating a `HOTEL_PROPERTY` asset set yourself fails with `MUTATE_NOT_ALLOWED`. Brand guidelines cannot be used (`CANNOT_ENABLE_BRAND_GUIDELINES_FOR_TRAVEL_GOALS`). The campaigns overview mentions a `TRAVEL_GOALS` sub-type that does not exist in the v25 enum, so the docs conflict. | https://developers.google.com/google-ads/api/docs/performance-max/travel-goals, https://developers.google.com/google-ads/api/docs/campaigns/overview |
| Travel | `TRAVEL`, sub-type `TRAVEL_ACTIVITIES`, ad group `TRAVEL_ADS` | **(unconfirmed)** | Only `travel_campaign_settings.travel_account_id` (immutable) is documented. | No API creation guide exists; treat as allowlisted or UI-only **(unconfirmed)**. | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.TravelCampaignSettings |
| Local (legacy) | `LOCAL` with `LOCAL_CAMPAIGN` | No **(unconfirmed)** | Not applicable | Upgraded to Performance Max; `campaign.performance_max_upgrade` is output only. | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign, https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.PerformanceMaxUpgrade |
| Discovery (renamed) | Was `DISCOVERY`, now `DEMAND_GEN` | Not applicable | Use Demand Gen. | Renamed in every field, enum and error in v17; absent from the v25 enum. | https://developers.google.com/google-ads/api/docs/archived-release-notes |

**`AdvertisingChannelType` in v25, in full:** `UNSPECIFIED`, `UNKNOWN` (return only), `SEARCH`, `DISPLAY`, `SHOPPING`, `HOTEL`, `VIDEO`, `MULTI_CHANNEL` (App), `LOCAL`, `SMART`, `PERFORMANCE_MAX`, `LOCAL_SERVICES`, `TRAVEL`, `DEMAND_GEN` (https://developers.google.com/google-ads/api/reference/rpc/v25/AdvertisingChannelTypeEnum.AdvertisingChannelType).

**`AdvertisingChannelSubType` in v25, in full:** `UNSPECIFIED`, `UNKNOWN`, `SEARCH_MOBILE_APP`, `DISPLAY_MOBILE_APP`, `SEARCH_EXPRESS`, `DISPLAY_EXPRESS`, `SHOPPING_SMART_ADS` (cannot be created), `DISPLAY_GMAIL_AD`, `DISPLAY_SMART_CAMPAIGN` (cannot be created), `VIDEO_ACTION`, `VIDEO_NON_SKIPPABLE`, `APP_CAMPAIGN`, `APP_CAMPAIGN_FOR_ENGAGEMENT`, `LOCAL_CAMPAIGN`, `SHOPPING_COMPARISON_LISTING_ADS`, `SMART_CAMPAIGN`, `VIDEO_SEQUENCE`, `APP_CAMPAIGN_FOR_PRE_REGISTRATION`, `VIDEO_REACH_TARGET_FREQUENCY`, `TRAVEL_ACTIVITIES`, `YOUTUBE_AUDIO`. There is no `TRAVEL_GOALS` and no `VIDEO_EFFICIENT_REACH` sub-type; `VIDEO_OUTSTREAM` was removed in v19 (https://developers.google.com/google-ads/api/reference/rpc/v25/AdvertisingChannelSubTypeEnum.AdvertisingChannelSubType). For a standard Search or Performance Max campaign, leave the sub-type unset.

## 10. Versions

Release notes for v23 onwards are at https://developers.google.com/google-ads/api/docs/release-notes, v22 and earlier at https://developers.google.com/google-ads/api/docs/archived-release-notes, and sunset dates at https://developers.google.com/google-ads/api/docs/sunset-dates.

**Live versions on 12 November 2026:** v23, v24, v25 and v26 (the latest is v26.2, released 11 November 2026). v19 to v22 are sunset. A call to a major version always goes to its latest minor version. **v25 sunsets in August 2027** (https://developers.google.com/google-ads/api/docs/sunset-dates). PPCWay is one version behind the newest; it has about nine months before it must move.

| Version | Release date | Sunset date | Creation-relevant changes | Source |
|---|---|---|---|---|
| v19 (v19.1 16 Apr 2025, v19.2 6 Aug 2025) | 26 Feb 2025 | 11 Feb 2026 (sunset) | All feed entities removed (`Feed`, `FeedMapping`, `FeedService`, `AdGroupFeed` and others); use assets. `VIDEO_OUTSTREAM` removed. Performance Max brand guidelines (allowlisted then): `brand_guidelines_enabled` set only at create, `Campaign.brand_guidelines` (colours, font), `CampaignService.EnablePMaxBrandGuidelines`. v19.1: Demand Gen ad group channel controls, read-only `YOUTUBE_AUDIO`, Performance Max brand exclusion override. v19.2: `Campaign.contains_eu_political_advertising` added (not enforced in v19 or v20). | https://developers.google.com/google-ads/api/docs/archived-release-notes |
| v20 (v20.1 6 Aug 2025, v20.2 25 Feb 2026) | 4 Jun 2025 | 10 Jun 2026 (sunset) | Campaign-level negative keywords for Performance Max. v20.1: EU political advertising field. v20.2: `Customer.contains_eu_political_advertising` and `Campaign.missing_eu_political_advertising_declaration`. | https://developers.google.com/google-ads/api/docs/archived-release-notes |
| v21 (v21.1 25 Feb 2026, v21.2 24 Jun 2026) | 6 Aug 2025 | 5 Aug 2026 (sunset) | **`contains_eu_political_advertising` required on create** (`FieldError.REQUIRED`). Performance Max `brand_guidelines_enabled` defaults to true. **AI Max for Search arrives**: `Campaign.ai_max_setting.enable_ai_max`, `bundling_required`, `AdGroup.ai_max_ad_group_setting.disable_search_term_matching`, `CampaignError.AI_MAX_MUST_BE_ENABLED`, ad group brand lists, locations and URL rules. `FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION`. `AutomaticallyCreatedAssetRemovalService`. `TargetRoas.target_roas_tolerance_percent_millis` (10,000 to 30,000). | https://developers.google.com/google-ads/api/docs/archived-release-notes |
| v22 (v22.1 25 Feb 2026, v22.2 24 Jun 2026) | 15 Oct 2025 | 7 Oct 2026 (sunset) | **`Campaign.url_expansion_opt_out` removed**; use `FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION`. Performance Max asset performance labels removed. **`AssetGenerationService`** (`GenerateText`, `GenerateImages`) added as a closed beta. Demand Gen target CPC (`Campaign.target_cpc`, `AdGroup.target_cpc_micros`). Performance Max `GENERATE_IMAGE_ENHANCEMENT` (on by default) and `GENERATE_IMAGE_EXTRACTION`. Negative keyword shared sets for App and Local. `GoalService` and `CampaignGoalConfigService` appear in the v22 reference; the version they first arrived in is **(unconfirmed)**. Batch jobs limited to 10,000 operations per add request. | https://developers.google.com/google-ads/api/docs/archived-release-notes, https://developers.google.com/google-ads/api/reference/rpc/v22/GoalService |
| v23 (v23.1 25 Feb, v23.2 25 Mar, v23.3 24 Jun 2026) | 28 Jan 2026 | February 2027 | **`Campaign.start_date` and `end_date` removed**; use `start_date_time` and `end_date_time`. `CallAd` and `CallAdInfo` removed. One ad can no longer be shared across ad groups (`AD_SHARING_NOT_ALLOWED`). Total budget errors `DURATION_TOO_LONG_FOR_TOTAL_BUDGET` and `END_DATE_TIME_REQUIRED_FOR_TOTAL_BUDGET`. Vertical ads feed for Search with AI Max. v23.1: **`Campaign.text_guidelines`** (Search and Performance Max). v23.2: `AdGroupAd.start_date_time` and `end_date_time`. | https://developers.google.com/google-ads/api/docs/release-notes |
| v24 (v24.1 13 May, v24.2 24 Jun 2026) | 22 Apr 2026 | May 2027 (the table lists June 2027 against v24.2) | `DemandGenVideoResponsiveAdInfo` requires `videos` and `logo_images`. **`KeywordPlanIdeaService.GenerateKeywordForecastMetrics` reshaped**: `geo_modifiers` replaced by `CampaignToForecast.geo_target_constants`, `biddable_keywords` by `ForecastAdGroup.keywords`; `keyword_plan_network`, `negative_keywords`, `max_cpc_bid_micros`, `BiddableKeyword`, `CriterionBidModifier` and forecast `impressions` and `click_through_rate` removed. Gender exclusions for Performance Max. v24.1: experiment types `ADOPT_AI_MAX` and `ADOPT_BROAD_MATCH_KEYWORDS`. v24.2: `ignore_brand_exclusion_in_shopping_ads`, `SmartCampaignError.CREATION_FAILED`, `CriterionError.CANNOT_TARGET_LANGUAGE`. | https://developers.google.com/google-ads/api/docs/release-notes |
| **v25** (v25.1 19 Aug, v25.2 23 Sep 2026) | 22 Jul 2026 | **August 2027** | **`CustomerLifecycleGoal`, `CampaignLifecycleGoal` and their services removed**, with `CustomerAcquisitionGoalSettings` and `LifecycleGoalValueSettings`; use `Goal.new_customer_acquisition_goal_settings` and `CampaignGoalConfig.campaign_new_customer_acquisition_settings`. Loyalty retention goal. New Demand Gen multi-asset ads opted in to `GENERATE_ANIMATED_IMAGES_FROM_OTHER_ASSETS`. v25.1: `Campaign.aca_migration_date_time` and `broad_match_migration_date_time` (output only). v25.2: URL options on `AssetGroup`, Performance Max `AUTOMATED_VIDEO_CRAWL`, `SmartCampaignSettingService.GeneratePMaxDraftCampaign`. | https://developers.google.com/google-ads/api/docs/release-notes, https://developers.google.com/ads/blog/posts/2026/07/announcing-v25-of-google-ads-api |
| v26 (v26.1 28 Oct, v26.2 11 Nov 2026), for context | 14 Oct 2026 | November 2027 | Local Services Performance Max creation. EU declaration optional for campaigns that do not target the EU. `CurrencyConstant.demand_gen_info.minimum_budget_per_day_micros`. Shopping `listing_type`. Performance Max household income exclusions (v26.2). | https://developers.google.com/google-ads/api/docs/release-notes |

`Campaign.keyword_match_type` was added in v17, before this range. Enhanced CPC was switched off for Search and Display outside the versioned notes (week of 31 March 2025). No change to Performance Max search theme limits was found in v19 to v25 **(unconfirmed)**.

### 10.1 Deprecated: avoid when creating campaigns

| Item | Status | Replacement | Source |
|---|---|---|---|
| `campaign_criterion.language` on SEARCH | Rejected since late September 2026 in every version, with `ContextError.OPERATION_NOT_PERMITTED_FOR_CONTEXT`. **PPCWay sends it today.** | None; Google matches language from the ad and landing page | https://developers.google.com/google-ads/api/docs/deprecations, https://developers.google.com/ads/blog/posts/2026/08/google-ads-language-targeting-changes |
| Developer token header | Developer tokens "are deprecated and have been sunset" (9 September 2026). The header is optional and ignored; the access level comes from the Google Cloud project that owns the OAuth client | Cloud project access | https://developers.google.com/google-ads/api/docs/deprecations, https://developers.google.com/google-ads/api/docs/api-policy/developer-token |
| `Campaign.start_date`, `end_date` | Removed in v23 | `start_date_time`, `end_date_time` | https://developers.google.com/google-ads/api/docs/release-notes |
| Leaving out `contains_eu_political_advertising` | Required since v21; v26 relaxes it only for campaigns that do not target the EU | Always send it | https://developers.google.com/google-ads/api/docs/archived-release-notes, https://developers.google.com/google-ads/api/docs/api-policy/eu-par |
| `Campaign.keyword_match_type = BROAD` | New settings blocked from 3 August 2026 in every version (`CANNOT_SET_CAMPAIGN_KEYWORD_MATCH_TYPE`); removed from versions released after 1 September 2026; existing ones moved to AI Max in September 2026 | AI Max, plus ad group `disable_search_term_matching` | https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns/getting-started, https://developers.google.com/ads/blog/posts/2026/08/migrate-campaign-level-broad-match-and |
| Legacy automatically created assets | Blocked from 3 August 2026; moved in September 2026 | AI Max plus `TEXT_ASSET_AUTOMATION` | https://developers.google.com/ads/blog/posts/2026/08/migrate-campaign-level-broad-match-and |
| `Campaign.url_expansion_opt_out` | Removed in v22 | `FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION` | https://developers.google.com/google-ads/api/docs/archived-release-notes |
| Dynamic Search Ads ad groups (`SEARCH_DYNAMIC_ADS`) | No new ones from February 2027; existing ones upgraded to AI Max | AI Max | https://developers.google.com/ads/blog/posts/2026/08/migrate-campaign-level-broad-match-and |
| Enhanced CPC (`ManualCpc.enhanced_cpc_enabled`, `EnhancedCpc` portfolio) | Not available for Search or Display since the week of 31 March 2025; the field remains in v25 unmarked; the portfolio scheme cannot be created | `manual_cpc`, `target_spend`, `maximize_conversions` | https://support.google.com/google-ads/answer/2464964, https://developers.google.com/google-ads/api/reference/rpc/v25/EnhancedCpc |
| `TargetSpend.target_spend_micros` | Deprecated | Leave unset; optionally `cpc_bid_ceiling_micros` | https://developers.google.com/google-ads/api/reference/rpc/v25/TargetSpend |
| Standalone `target_cpa`, `target_roas` on a campaign | Portfolio only | Targets inside `maximize_conversions` or `maximize_conversion_value` | https://developers.google.com/google-ads/api/docs/campaigns/bidding/strategy-types |
| Geo target type `SEARCH_INTEREST` | **Not removed** in v25; still valid for Search and standard Shopping | `PRESENCE` (PPCWay's value) is fine | https://developers.google.com/google-ads/api/reference/rpc/v25/PositiveGeoTargetTypeEnum.PositiveGeoTargetType |
| Call-only ads (`CallAdInfo`) | Creation blocked from January 2026; removed in v23; existing ones stop serving February 2027 | Responsive search ad plus call asset | https://developers.google.com/ads/blog/posts/2025/10/upgrade-your-call-only-ads-to, https://developers.google.com/google-ads/api/docs/deprecations |
| Expanded text ads | Deprecated | Responsive search ad | https://developers.google.com/google-ads/api/reference/rpc/v25/ExpandedTextAdInfo |
| Feed-based extensions | Removed in v19 | Assets | https://developers.google.com/google-ads/api/docs/archived-release-notes |
| Smart campaigns | Creation blocked from 23 September 2026 | Search, Performance Max or Demand Gen | https://developers.google.com/google-ads/api/docs/deprecations |
| Smart Shopping, Smart Display | Cannot be created | Performance Max | https://developers.google.com/google-ads/api/reference/rpc/v25/AdvertisingChannelSubTypeEnum.AdvertisingChannelSubType |
| Video Action, and creating any Video campaign | Video Action removed April 2025; all Video campaigns read-only through the API | Demand Gen | https://developers.google.com/google-ads/api/docs/video/overview |
| `DISCOVERY` | Renamed in v17 | `DEMAND_GEN` | https://developers.google.com/google-ads/api/docs/archived-release-notes |
| Local campaigns | Legacy, upgraded to Performance Max | Performance Max | https://developers.google.com/google-ads/api/reference/rpc/v25/Campaign.PerformanceMaxUpgrade |
| Similar audiences (`SimilarUserListInfo`) | Read-only | First-party lists or audience signals **(unconfirmed)** | https://developers.google.com/google-ads/api/reference/rpc/v25/SimilarUserListInfo |
| Forecasts through saved keyword plans | `KeywordPlanService` exposes only `MutateKeywordPlans` in v25; forecast fields removed in v24 | `KeywordPlanIdeaService.GenerateKeywordForecastMetrics` | https://developers.google.com/google-ads/api/reference/rpc/v25/KeywordPlanService, https://developers.google.com/google-ads/api/docs/release-notes |
| `CustomerLifecycleGoal`, `CampaignLifecycleGoal` | Removed in v25 | `GoalService`, `CampaignGoalConfigService` | https://developers.google.com/google-ads/api/docs/release-notes |

## 11. Recommended creation order

Both orders follow the same rules from section 1: every resource is created before anything refers to it; temporary ids are negative and unique across the whole request; operations of the same type sit next to each other; `partialFailure` is false; and the same body is sent first with `validateOnly: true` and then for real (https://developers.google.com/google-ads/api/docs/mutating/best-practices, https://developers.google.com/google-ads/api/docs/batch-processing/temporary-ids). Steps marked optional can be left out without breaking the request.

### 11.1 One atomic Search campaign

**Before the request (reads and lookups, not part of the Mutate):**

- `GeoTargetConstantService.SuggestGeoTargetConstants` for the places (already used).
- `KeywordPlanIdeaService.GenerateKeywordIdeas` for keywords (already used), and optionally `GenerateKeywordForecastMetrics` and `RecommendationService.GenerateRecommendations` for budget and bidding suggestions.
- `SELECT customer_conversion_goal.category, customer_conversion_goal.origin, customer_conversion_goal.biddable FROM customer_conversion_goal`, if the campaign will choose its own goals.
- `BrandSuggestionService.SuggestBrands`, only if AI Max brand lists are used.

**The request, in order:**

1. `campaignBudgetOperation.create` (`campaignBudgets/-1`): `name` (unique), `amountMicros`, `deliveryMethod: STANDARD`, `explicitlyShared: false`; or `period: CUSTOM_PERIOD` with `totalAmountMicros` for a total budget.
2. Optional: `biddingStrategyOperation.create` (`biddingStrategies/-2`), only for a portfolio strategy.
3. Optional: `sharedSetOperation.create` for a `NEGATIVE_KEYWORDS` list (`sharedSets/-3`), and a `BRANDS` list (`sharedSets/-4`) if AI Max brand controls are used.
4. Optional: `sharedCriterionOperation.create`, one per keyword in the negative list and one per brand.
5. Optional: `assetOperation.create`, one per new asset (`assets/-10`, `-11` and so on): sitelinks, callouts, structured snippets, call, price, promotion, lead form, business name text, logo image, ad images.
6. Optional: `customerAssetOperation.create`, for assets that should apply account-wide (such as the call asset or business name).
7. `campaignOperation.create` (`campaigns/-20`): `name`, `status`, `advertisingChannelType: SEARCH`, `campaignBudget: campaignBudgets/-1`, one bidding member (`targetSpend`, `maximizeConversions` with optional `targetCpaMicros`, `maximizeConversionValue` with optional `targetRoas`, `targetImpressionShare`, `manualCpc`, or `biddingStrategy: biddingStrategies/-2`), `networkSettings`, `geoTargetTypeSetting`, `containsEuPoliticalAdvertising`, optional `startDateTime` and `endDateTime` (`yyyy-MM-dd HH:mm:ss`, required end with a total budget), optional `trackingUrlTemplate`, `finalUrlSuffix`, `urlCustomParameters`, optional `aiMaxSetting.enableAiMax` with `assetAutomationSettings` and `textGuidelines`. Do not send `keywordMatchType`.
8. `campaignCriterionOperation.create`, all together: locations (included and excluded), optional proximity and location groups, optional ad schedule entries and device entries (each with `bidModifier`), campaign negative keywords, optional IP blocks, optional `brandList` (AI Max), optional user lists in observation. **No language criterion.**
9. Optional: `campaignBidModifierOperation.create` for the calls interaction type (confirmed as a `MutateOperation` member on https://developers.google.com/google-ads/api/reference/rpc/v25/MutateOperation).
10. Optional: `campaignSharedSetOperation.create`, linking `sharedSets/-3` to `campaigns/-20`.
11. Optional: `campaignAssetOperation.create`, one per campaign-level asset link, with its `fieldType` (`SITELINK`, `CALLOUT`, `STRUCTURED_SNIPPET`, `CALL`, `PRICE`, `PROMOTION`, `LEAD_FORM`, `BUSINESS_NAME`, `BUSINESS_LOGO`, `AD_IMAGE`).
12. Optional: `campaignConversionGoalOperation.update`, one per category and origin pair, resource `campaignConversionGoals/-20~{category}~{origin}`, `updateMask: biddable`.
13. `adGroupOperation.create`, one per theme (`adGroups/-30`, `-31` and so on): `name`, `campaign: campaigns/-20`, `status`, `type: SEARCH_STANDARD`, optional `cpcBidMicros` (manual CPC only), optional `aiMaxAdGroupSetting`.
14. `adGroupCriterionOperation.create`, all together: keywords with match types, optional ad group negatives, optional audiences; on a resend after a keyword policy finding, add `exemptPolicyViolationKeys`.
15. `adGroupAdOperation.create`, one responsive search ad per ad group (up to 3 enabled): `headlines` (3 to 15, optional `pinnedField`), `descriptions` (2 to 4), optional `path1` and `path2`, `finalUrls`; on a resend after an ad policy finding, add `policyValidationParameter.ignorablePolicyTopics`.
16. Optional: `adGroupAssetOperation.create`, for ad-group-specific sitelinks, callouts or images.
17. Optional: `adGroupBidModifierOperation.create`, for ad-group device adjustments.

**After the request (separate calls):**

- New customer acquisition: `GoalService.MutateGoals` once per account, then `CampaignGoalConfigService.MutateCampaignGoalConfigs` for the new campaign id (section 7).
- A custom conversion goal, if one is wanted: a second Mutate after the campaign exists (section 7.1).
- Read back `ad_group_ad.ad_strength`, `ad_group_ad.action_items` and `ad_group_ad.policy_summary` to show Ad Strength and review status (section 4.4).

### 11.2 One atomic Performance Max campaign

This follows Google's structure guide: every asset is created before the contiguous run of asset group asset links, the brand assets ride in the same request as the campaign, and the asset group arrives with all its minimum assets (https://developers.google.com/google-ads/api/performance-max/structure-requests, https://developers.google.com/google-ads/api/performance-max/getting-started).

**Before the request:** confirm the account has conversion tracking; for retail, confirm the Merchant Center link; read `customer_conversion_goal` if the campaign will choose its own goals; use `BrandSuggestionService.SuggestBrands` if brands will be excluded.

**The request, in order:**

1. `campaignBudgetOperation.create` (`campaignBudgets/-1`): `amountMicros`, `period: DAILY`, `deliveryMethod: STANDARD`, `explicitlyShared: false`.
2. Optional: `sharedSetOperation.create` for a `BRANDS` list (`sharedSets/-4`), then `sharedCriterionOperation.create` for each brand, if brands are excluded.
3. `assetOperation.create` for every new asset (`assets/-10` onwards): 3 to 15 headlines, 1 to 5 long headlines, 2 to 5 descriptions (one of 60 characters or fewer), 1 business name, 1 to 5 logos, 1 to 20 landscape and 1 to 20 square marketing images, optional portrait images, optional YouTube videos (up to 15), optional call to action, and any campaign-level sitelinks or callouts.
4. `campaignOperation.create` (`campaigns/-2`): `advertisingChannelType: PERFORMANCE_MAX`, `campaignBudget: campaignBudgets/-1`, `maximizeConversions` (optional `targetCpaMicros`) or `maximizeConversionValue` (optional `targetRoas`), `containsEuPoliticalAdvertising`, `brandGuidelinesEnabled` (default true) with optional `brandGuidelines`, optional `assetAutomationSettings` (for example `FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION` opted out), optional `textGuidelines`, `geoTargetTypeSetting`, optional dates, `shoppingSetting.merchantId` for retail, and `status` (Google recommends `PAUSED`; the campaign is the only entity whose status should be set).
5. `campaignAssetOperation.create`: with brand guidelines on, exactly one `BUSINESS_NAME` and at least one `LOGO` (optional `LANDSCAPE_LOGO`), plus any campaign-level sitelinks or callouts.
6. Optional: `campaignCriterionOperation.create`, all together: locations, language (allowed for Performance Max), ad schedule, device, age, gender exclusions, negative keywords, `brandList` with `negative: true`, and `webpage` with `negative: true` for URL exclusions.
7. Optional: `campaignConversionGoalOperation.update`, one per category and origin pair (`campaignConversionGoals/-2~{category}~{origin}`), as in Google's sample.
8. `assetGroupOperation.create` (`assetGroups/-3`): `name`, `campaign: campaigns/-2`, `finalUrls`, optional `path1` and `path2`, optional URL options (v25.2).
9. `assetGroupAssetOperation.create`, one contiguous run linking every asset from step 3 with its `fieldType` (`HEADLINE`, `LONG_HEADLINE`, `DESCRIPTION`, `MARKETING_IMAGE`, `SQUARE_MARKETING_IMAGE`, `PORTRAIT_MARKETING_IMAGE`, `YOUTUBE_VIDEO`, `CALL_TO_ACTION_SELECTION`; `BUSINESS_NAME` and `LOGO` here only when brand guidelines are off), meeting every minimum.
10. Optional: `assetGroupSignalOperation.create`: audience signals (an `audience` resource) and search themes. These can also be added in a later request.
11. Retail only: `assetGroupListingGroupFilterOperation.create` (`assetGroupListingGroupFilters/-4`): a root node with `type: UNIT_INCLUDED` and `listingSource: SHOPPING` to cover all products, or a full subdivision tree.

**After the request:** new customer acquisition and retention goals through `GoalService` and `CampaignGoalConfigService`; optionally `ShareablePreviewService.GenerateShareablePreviews` on the new asset group to show the merchant a preview; read back `asset_group.ad_strength` and `asset_group.asset_coverage`.
