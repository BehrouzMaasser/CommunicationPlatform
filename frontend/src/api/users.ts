import { apiGet } from './client'
import type { PaginatedResponse } from '../types/friendships'
import type { PublicUser } from '../types/users'


export async function searchUsers(
  search: string,
): Promise<PublicUser[]> {
  const params = new URLSearchParams({
    search,
  })

  const response =
    await apiGet<PaginatedResponse<PublicUser>>(
      `/api/v1/users/?${params.toString()}`,
    )

  return response.results
}
