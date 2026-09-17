function DirectMessagesIndexPage() {
  return (
    <div className="dm-empty-pane">
      <div className="dm-empty-pane-icon">
        <span aria-hidden="true">✉</span>
      </div>
      <h2 className="h4 mb-2">
        Your direct messages
      </h2>
      <p className="text-secondary mb-0">
        Choose a conversation from the list to start messaging.
      </p>
    </div>
  )
}


export default DirectMessagesIndexPage
