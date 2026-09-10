class FriendshipsError(Exception):
    """Base exception for expected Friends-domain failures."""

    code = "friendships_error"
    default_message = "A friendships domain error occurred."

    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(self.message)


class TargetUserNotFound(FriendshipsError):
    code = "target_user_not_found"
    default_message = "The target user does not exist."


class FriendRequestNotFound(FriendshipsError):
    code = "friend_request_not_found"
    default_message = "The friend request does not exist."


class FriendshipNotFound(FriendshipsError):
    code = "friendship_not_found"
    default_message = "The friendship does not exist."


class SelfFriendRequestNotAllowed(FriendshipsError):
    code = "self_friend_request_not_allowed"
    default_message = "A user cannot send a friend request to themselves."


class UsersAlreadyFriends(FriendshipsError):
    code = "users_already_friends"
    default_message = "The users are already friends."


class FriendRequestAlreadyPending(FriendshipsError):
    code = "friend_request_already_pending"
    default_message = "A friend request is already pending between these users."


class FriendRequestRecipientRequired(FriendshipsError):
    code = "friend_request_recipient_required"
    default_message = "Only the recipient may perform this operation."


class FriendRequestSenderRequired(FriendshipsError):
    code = "friend_request_sender_required"
    default_message = "Only the sender may perform this operation."


class SelfFriendshipNotAllowed(FriendshipsError):
    code = "self_friendship_not_allowed"
    default_message = "A friendship cannot contain the same user twice."
