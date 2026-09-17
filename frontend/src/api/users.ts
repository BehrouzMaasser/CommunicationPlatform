import {
  apiRequest,
} from './client'
import { getAllPages } from './pagination'
import type {
  CurrentUser,
  PublicUser,
} from '../types/users'


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


export function updateCurrentUserAvatar(
  file: File,
): Promise<CurrentUser> {
  const body = new FormData()
  body.append(
    'avatar',
    file,
  )

  return apiRequest<CurrentUser>(
    '/api/v1/users/me/avatar/',
    {
      method: 'PUT',
      body,
    },
  )
}


export function removeCurrentUserAvatar(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>(
    '/api/v1/users/me/avatar/',
    {
      method: 'DELETE',
    },
  )
}
