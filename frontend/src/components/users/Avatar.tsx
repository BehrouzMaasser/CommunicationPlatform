import {
  useState,
} from 'react'

import type {
  PublicUser,
} from '../../types/users'


type AvatarSize =
  | 'sm'
  | 'md'
  | 'lg'
  | 'xl'


type AvatarProps = {
  user: Pick<
    PublicUser,
    'username' | 'avatar_url'
  >
  size?: AvatarSize
  className?: string
  alt?: string
}


function getInitials(
  username: string,
): string {
  const parts =
    username
      .trim()
      .split(/[\s._-]+/)
      .filter(Boolean)

  if (parts.length >= 2) {
    return (
      parts[0].charAt(0)
      + parts[1].charAt(0)
    ).toUpperCase()
  }

  return (
    parts[0]
      ?.slice(0, 2)
      .toUpperCase()
    ?? '?'
  )
}


function Avatar({
  user,
  size = 'md',
  className = '',
  alt,
}: AvatarProps) {
  const [
    failedAvatarUrl,
    setFailedAvatarUrl,
  ] = useState<string | null>(null)

  const classes = [
    'user-avatar',
    `user-avatar-${size}`,
    className,
  ]
    .filter(Boolean)
    .join(' ')

  if (
    user.avatar_url
    && failedAvatarUrl
      !== user.avatar_url
  ) {
    return (
      <img
        className={classes}
        src={user.avatar_url}
        alt={
          alt
          ?? `${user.username} avatar`
        }
        onError={() => {
          setFailedAvatarUrl(
            user.avatar_url,
          )
        }}
      />
    )
  }

  const isDecorative = alt === ''

  return (
    <span
      className={`${classes} user-avatar-fallback`}
      role={
        isDecorative
          ? undefined
          : 'img'
      }
      aria-hidden={
        isDecorative
          ? true
          : undefined
      }
      aria-label={
        isDecorative
          ? undefined
          : (
              alt
              ?? `${user.username} avatar`
            )
      }
    >
      {getInitials(user.username)}
    </span>
  )
}


export default Avatar
