from typing import Literal


ConversationType = Literal["dm", "group"]


def user_group_name(user_id: int) -> str:
    return f"user.{user_id}"


def conversation_group_name(
    conversation_type: ConversationType,
    conversation_id: int,
) -> str:
    if conversation_type == "dm":
        return f"dm.{conversation_id}"

    if conversation_type == "group":
        return f"group.{conversation_id}"

    raise ValueError(
        "Unsupported conversation type."
    )
