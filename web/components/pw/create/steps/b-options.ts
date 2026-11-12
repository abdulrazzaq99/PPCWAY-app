import type { PriceItem, Price } from "@/lib/creation";

/*
  Google's fixed lists for assets, with the words its screens use. The values
  are the v25 enum names the server sends on unchanged (`builder/ops.py`).
*/

type Option<T extends string = string> = { value: T; label: string };

const options = <T extends string>(pairs: [T, string][]): Option<T>[] =>
  pairs.map(([value, label]) => ({ value, label }));

/** Structured snippet headers, in English, as Google's header list has them. */
export const SNIPPET_HEADERS = [
  "Amenities",
  "Brands",
  "Courses",
  "Degree programs",
  "Destinations",
  "Featured hotels",
  "Insurance coverage",
  "Models",
  "Neighborhoods",
  "Service catalog",
  "Shows",
  "Styles",
  "Types",
] as const;

export const PRICE_TYPES = options([
  ["BRANDS", "Brands"],
  ["EVENTS", "Events"],
  ["LOCATIONS", "Locations"],
  ["NEIGHBORHOODS", "Neighborhoods"],
  ["PRODUCT_CATEGORIES", "Product categories"],
  ["PRODUCT_TIERS", "Product tiers"],
  ["SERVICES", "Services"],
  ["SERVICE_CATEGORIES", "Service categories"],
  ["SERVICE_TIERS", "Service tiers"],
]);

export const PRICE_QUALIFIERS = options<Price["qualifier"]>([
  ["", "No qualifier"],
  ["FROM", "From"],
  ["UP_TO", "Up to"],
  ["AVERAGE", "Average"],
]);

export const PRICE_UNITS = options<PriceItem["unit"]>([
  ["", "No unit"],
  ["PER_HOUR", "Per hour"],
  ["PER_DAY", "Per day"],
  ["PER_WEEK", "Per week"],
  ["PER_MONTH", "Per month"],
  ["PER_YEAR", "Per year"],
  ["PER_NIGHT", "Per night"],
]);

export const OCCASIONS = options([
  ["", "None"],
  ["NEW_YEARS", "New Year's"],
  ["CHINESE_NEW_YEAR", "Chinese New Year"],
  ["VALENTINES_DAY", "Valentine's Day"],
  ["EASTER", "Easter"],
  ["MOTHERS_DAY", "Mother's Day"],
  ["FATHERS_DAY", "Father's Day"],
  ["LABOR_DAY", "Labor Day"],
  ["BACK_TO_SCHOOL", "Back to school"],
  ["HALLOWEEN", "Halloween"],
  ["BLACK_FRIDAY", "Black Friday"],
  ["CYBER_MONDAY", "Cyber Monday"],
  ["CHRISTMAS", "Christmas"],
  ["BOXING_DAY", "Boxing Day"],
  ["INDEPENDENCE_DAY", "Independence Day"],
  ["NATIONAL_DAY", "National Day"],
  ["END_OF_SEASON", "End of season"],
  ["WINTER_SALE", "Winter sale"],
  ["SUMMER_SALE", "Summer sale"],
  ["FALL_SALE", "Fall sale"],
  ["SPRING_SALE", "Spring sale"],
  ["RAMADAN", "Ramadan"],
  ["EID_AL_FITR", "Eid al-Fitr"],
  ["EID_AL_ADHA", "Eid al-Adha"],
  ["SINGLES_DAY", "Singles Day"],
  ["WOMENS_DAY", "Women's Day"],
  ["HOLI", "Holi"],
  ["PARENTS_DAY", "Parents' Day"],
  ["ST_NICHOLAS_DAY", "St. Nicholas Day"],
  ["CARNIVAL", "Carnival"],
  ["EPIPHANY", "Epiphany"],
  ["ROSH_HASHANAH", "Rosh Hashanah"],
  ["PASSOVER", "Passover"],
  ["HANUKKAH", "Hanukkah"],
  ["DIWALI", "Diwali"],
  ["NAVRATRI", "Navratri"],
  ["SONGKRAN", "Songkran"],
  ["YEAR_END_GIFT", "Year-end gift"],
]);

/** Google's "Promotion type", which the server keeps as a kind and an "up to" flag. */
export const PROMOTION_TYPES = options([
  ["money", "Monetary discount"],
  ["percent", "Percent discount"],
  ["up_to_money", "Up to monetary discount"],
  ["up_to_percent", "Up to percent discount"],
]);

export const PROMOTION_DETAILS = options<"none" | "orders_over" | "code">([
  ["none", "None"],
  ["orders_over", "On orders over"],
  ["code", "Promo code"],
]);

export const LEAD_CTAS = options([
  ["LEARN_MORE", "Learn more"],
  ["GET_QUOTE", "Get quote"],
  ["APPLY_NOW", "Apply now"],
  ["SIGN_UP", "Sign up"],
  ["CONTACT_US", "Contact us"],
  ["SUBSCRIBE", "Subscribe"],
  ["DOWNLOAD", "Download"],
  ["BOOK_NOW", "Book now"],
  ["GET_OFFER", "Get offer"],
  ["REGISTER", "Register"],
  ["GET_INFO", "Get info"],
  ["REQUEST_DEMO", "Request demo"],
  ["JOIN_NOW", "Join now"],
  ["GET_STARTED", "Get started"],
]);

export const LEAD_FIELDS = options([
  ["FULL_NAME", "Full name"],
  ["EMAIL", "Email"],
  ["PHONE_NUMBER", "Phone number"],
  ["POSTAL_CODE", "Postal code"],
  ["CITY", "City"],
  ["COUNTRY", "Country"],
  ["COMPANY_NAME", "Company name"],
  ["JOB_TITLE", "Job title"],
]);

/** Performance Max's call to action; empty is Google's "Automated". */
export const PMAX_CTAS = options([
  ["", "Automated"],
  ["APPLY_NOW", "Apply now"],
  ["BOOK_NOW", "Book now"],
  ["BUY_NOW", "Buy now"],
  ["CONTACT_US", "Contact us"],
  ["DONATE_NOW", "Donate now"],
  ["DOWNLOAD", "Download"],
  ["GET_QUOTE", "Get quote"],
  ["LEARN_MORE", "Learn more"],
  ["ORDER_NOW", "Order now"],
  ["PLAY_NOW", "Play now"],
  ["SEE_MORE", "See more"],
  ["SHOP_NOW", "Shop now"],
  ["SIGN_UP", "Sign up"],
  ["START_NOW", "Start now"],
  ["SUBSCRIBE", "Subscribe"],
  ["VISIT_SITE", "Visit site"],
  ["WATCH_NOW", "Watch now"],
]);

export const CTA_LABEL: Record<string, string> = Object.fromEntries(
  PMAX_CTAS.filter((o) => o.value).map((o) => [o.value, o.label]),
);

export const STORES = options<"GOOGLE_APP_STORE" | "APPLE_APP_STORE">([
  ["GOOGLE_APP_STORE", "Google Play"],
  ["APPLE_APP_STORE", "Apple App Store"],
]);
