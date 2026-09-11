export type PublicUser = {
  id: number
  username: string
}

export type CurrentUser = PublicUser & {
  email: string
}
