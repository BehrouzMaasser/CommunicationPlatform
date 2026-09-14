import { apiGet } from './client'


export type PaginatedResponse<T> = {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}


type ListResponse<T> =
  | T[]
  | PaginatedResponse<T>


function sameOriginPath(
  url: string,
): string {
  const parsed = new URL(
    url,
    window.location.origin,
  )

  return (
    parsed.pathname
    + parsed.search
    + parsed.hash
  )
}


export async function getPaginatedPage<T>(
  url: string,
): Promise<PaginatedResponse<T>> {
  const response =
    await apiGet<ListResponse<T>>(
      sameOriginPath(url),
    )

  if (Array.isArray(response)) {
    return {
      count: response.length,
      next: null,
      previous: null,
      results: response,
    }
  }

  return response
}


export async function getAllPages<T>(
  initialUrl: string,
): Promise<T[]> {
  const results: T[] = []
  const visited = new Set<string>()

  let nextUrl: string | null =
    sameOriginPath(initialUrl)

  while (nextUrl !== null) {
    if (visited.has(nextUrl)) {
      throw new Error(
        'Pagination returned a repeated page URL.',
      )
    }

    visited.add(nextUrl)

    const page: PaginatedResponse<T> = await getPaginatedPage<T>(nextUrl)

    results.push(...page.results)

    nextUrl = page.next
      ? sameOriginPath(page.next)
      : null
  }

  return results
}
