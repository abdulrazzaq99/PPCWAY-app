/*
  Money, written one way everywhere and safe on the server and in the browser.

  Dollars get the sign; any other currency gets its code after the number, the
  fastest way not to show a Canadian merchant euros. One fixed locale, not the
  visitor's: the server renders a page first and the browser renders it again,
  and two locales ("5 Nov" against "Nov 5") make React throw the server's page
  away.
*/
export function moneyOf(amount: number, currency = ""): string {
  const sign = !currency || currency === "CAD" || currency === "USD" ? "$" : "";
  const tail = sign ? "" : ` ${currency}`;
  return `${sign}${amount.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${tail}`;
}

/** Whole amounts for headline figures: "$1,240" rather than "$1,240.00" past a hundred. */
export function roundMoney(amount: number, currency = ""): string {
  if (Math.abs(amount) < 100) return moneyOf(amount, currency);
  const sign = !currency || currency === "CAD" || currency === "USD" ? "$" : "";
  const tail = sign ? "" : ` ${currency}`;
  return `${sign}${Math.round(amount).toLocaleString("en-GB")}${tail}`;
}
