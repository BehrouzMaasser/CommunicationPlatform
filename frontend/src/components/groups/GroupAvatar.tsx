type GroupAvatarSize =
  | 'sm'
  | 'md'
  | 'lg'


type GroupAvatarProps = {
  name: string
  size?: GroupAvatarSize
  className?: string
}


function getInitials(
  name: string,
): string {
  const parts =
    name
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


function GroupAvatar({
  name,
  size = 'md',
  className = '',
}: GroupAvatarProps) {
  const classes = [
    'group-avatar',
    `group-avatar-${size}`,
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <span
      className={classes}
      aria-hidden="true"
    >
      {getInitials(name)}
    </span>
  )
}


export default GroupAvatar
