export type PublicUser = {
  id: number
  username: string
  avatar_url: string | null
}

export type CurrentUser = PublicUser & {
  email: string
}
