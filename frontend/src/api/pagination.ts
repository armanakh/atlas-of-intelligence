export type CursorPage<T> = { items: readonly T[]; next_cursor: string | null }

/** Fetch every cursor page before exposing data for aggregate calculations. */
export async function collectAllPages<T>(fetchPage: (cursor: string | null) => Promise<CursorPage<T>>): Promise<T[]> {
  const result: T[] = []
  const seenCursors = new Set<string>()
  let cursor: string | null = null
  do {
    const page = await fetchPage(cursor)
    result.push(...page.items)
    cursor = page.next_cursor
    if (cursor && seenCursors.has(cursor)) throw new Error('Pagination returned a repeated cursor.')
    if (cursor) seenCursors.add(cursor)
  } while (cursor)
  return result
}
