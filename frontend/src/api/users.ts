import { getAllPages } from './pagination'
import type { PublicUser } from '../types/users'


export function searchUsers(
  search: string,
): Promise<PublicUser[]> {
  const params = new URLSearchParams({
    search,
  })

  return getAllPages<PublicUser>(
    `/api/v1/users/?${params.toString()}`,
  )
}
