type EmojiOption = {
  emoji: string
  label: string
}


const EMOJI_OPTIONS: EmojiOption[] = [
  { emoji: '😀', label: 'Grinning face' },
  { emoji: '😃', label: 'Smiling face' },
  { emoji: '😄', label: 'Smiling face with smiling eyes' },
  { emoji: '😁', label: 'Beaming face' },
  { emoji: '😂', label: 'Face with tears of joy' },
  { emoji: '🤣', label: 'Rolling on the floor laughing' },
  { emoji: '😊', label: 'Smiling face with smiling eyes' },
  { emoji: '😉', label: 'Winking face' },
  { emoji: '🥰', label: 'Smiling face with hearts' },
  { emoji: '😍', label: 'Heart eyes' },
  { emoji: '😎', label: 'Smiling face with sunglasses' },
  { emoji: '🤔', label: 'Thinking face' },
  { emoji: '😅', label: 'Grinning face with sweat' },
  { emoji: '🤗', label: 'Hugging face' },
  { emoji: '😭', label: 'Loudly crying face' },
  { emoji: '😢', label: 'Crying face' },
  { emoji: '😴', label: 'Sleeping face' },
  { emoji: '😡', label: 'Angry face' },
  { emoji: '👍', label: 'Thumbs up' },
  { emoji: '👎', label: 'Thumbs down' },
  { emoji: '👏', label: 'Clapping hands' },
  { emoji: '🙌', label: 'Raising hands' },
  { emoji: '🙏', label: 'Folded hands' },
  { emoji: '🤝', label: 'Handshake' },
  { emoji: '💪', label: 'Flexed biceps' },
  { emoji: '👀', label: 'Eyes' },
  { emoji: '❤️', label: 'Red heart' },
  { emoji: '🧡', label: 'Orange heart' },
  { emoji: '💛', label: 'Yellow heart' },
  { emoji: '💚', label: 'Green heart' },
  { emoji: '💙', label: 'Blue heart' },
  { emoji: '💜', label: 'Purple heart' },
  { emoji: '💯', label: 'Hundred points' },
  { emoji: '🔥', label: 'Fire' },
  { emoji: '🎉', label: 'Party popper' },
  { emoji: '🎊', label: 'Confetti ball' },
  { emoji: '✨', label: 'Sparkles' },
  { emoji: '⭐', label: 'Star' },
  { emoji: '✅', label: 'Check mark' },
  { emoji: '❌', label: 'Cross mark' },
  { emoji: '🚀', label: 'Rocket' },
  { emoji: '💬', label: 'Speech balloon' },
]


type EmojiPickerProps = {
  onSelect: (
    emoji: string,
  ) => void
}


function EmojiPicker({
  onSelect,
}: EmojiPickerProps) {
  return (
    <div
      className="emoji-picker"
      role="group"
      aria-label="Choose an emoji"
    >
      <div className="emoji-picker-title">
        Emoji
      </div>

      <div className="emoji-picker-grid">
        {EMOJI_OPTIONS.map(
          ({ emoji, label }) => (
            <button
              className="emoji-picker-option"
              type="button"
              key={`${emoji}-${label}`}
              aria-label={label}
              title={label}
              onClick={() =>
                onSelect(emoji)
              }
            >
              {emoji}
            </button>
          ),
        )}
      </div>
    </div>
  )
}


export default EmojiPicker
