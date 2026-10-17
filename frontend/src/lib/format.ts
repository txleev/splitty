/** "2" for 2, "1.5" for 1.5. */
export function formatQuantity(value: number): string {
  return String(Number(value.toFixed(3)))
}

/** Reads "2" or "1,5". Returns null unless it is a positive number within the backend limit. */
export function parseQuantity(text: string): number | null {
  const value = Number(text.trim().replace(',', '.'))
  return Number.isFinite(value) && value > 0 && value <= 10000 ? value : null
}
