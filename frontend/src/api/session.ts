import { apiGet } from './client'
import type { CurrentUser } from '../types/users'

export function getCurrentUser(): Promise<CurrentUser> {
  return apiGet<CurrentUser>('/api/v1/users/me/')
}
