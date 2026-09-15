/** Resolve a `?view=` value against the views a page draws, falling back to the first. */
export function pickView<const T extends readonly string[]>(
  views: T,
  value: string | undefined,
): T[number] {
  return (views as readonly string[]).includes(value ?? "") ? (value as T[number]) : views[0];
}
