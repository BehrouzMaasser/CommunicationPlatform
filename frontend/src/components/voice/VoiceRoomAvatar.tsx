import GroupAvatar from '../groups/GroupAvatar'


type Props = {
  name: string
  avatarUrl?: string | null
  size?: 'sm' | 'md' | 'lg'
  className?: string
}


function VoiceRoomAvatar({
  name,
  avatarUrl = null,
  size = 'md',
  className = '',
}: Props) {
  return (
    <GroupAvatar
      name={name}
      avatarUrl={avatarUrl}
      size={size}
      className={`voice-room-avatar ${className}`.trim()}
    />
  )
}


export default VoiceRoomAvatar
