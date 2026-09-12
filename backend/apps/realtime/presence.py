import time

from django.conf import settings
from redis.asyncio import Redis


class PresenceStore:
    """
    Ephemeral multi-connection presence leases.

    Production uses the Redis instance configured for Channels.
    InMemoryChannelLayer gets an in-process fallback so the existing realtime
    test suite does not require Redis.

    Presence is deliberately NOT persisted in PostgreSQL.
    """

    LEASE_SECONDS = 70
    KEY_TTL_SECONDS = 120

    _redis: Redis | None = None
    _memory_leases: dict[
        int,
        dict[str, float],
    ] = {}

    @classmethod
    def _uses_memory_backend(
        cls,
    ) -> bool:
        backend = (
            settings.CHANNEL_LAYERS[
                "default"
            ]["BACKEND"]
        )

        return backend.endswith(
            "InMemoryChannelLayer"
        )

    @classmethod
    def _redis_client(
        cls,
    ) -> Redis:
        if cls._redis is not None:
            return cls._redis

        config = (
            settings.CHANNEL_LAYERS[
                "default"
            ].get("CONFIG", {})
        )

        hosts = config.get(
            "hosts",
            [("localhost", 6379)],
        )

        first = hosts[0]

        if isinstance(first, str):
            cls._redis = Redis.from_url(
                first,
                decode_responses=True,
            )
            return cls._redis

        if isinstance(
            first,
            (tuple, list),
        ):
            host, port = first

            cls._redis = Redis(
                host=host,
                port=port,
                decode_responses=True,
            )
            return cls._redis

        if isinstance(first, dict):
            address = first.get(
                "address"
            )

            if isinstance(
                address,
                str,
            ):
                cls._redis = (
                    Redis.from_url(
                        address,
                        decode_responses=True,
                    )
                )
                return cls._redis

        raise RuntimeError(
            "Unsupported Redis channel-layer host configuration."
        )

    @staticmethod
    def _key(
        user_id: int,
    ) -> str:
        return (
            "realtime:presence:"
            f"{user_id}:connections"
        )

    @classmethod
    def _memory_prune(
        cls,
        *,
        user_id: int,
    ) -> None:
        now = time.time()

        leases = cls._memory_leases.get(
            user_id,
            {},
        )

        live = {
            connection_id: expires_at
            for connection_id, expires_at
            in leases.items()
            if expires_at > now
        }

        if live:
            cls._memory_leases[
                user_id
            ] = live
        else:
            cls._memory_leases.pop(
                user_id,
                None,
            )

    @classmethod
    async def _redis_prune(
        cls,
        *,
        user_id: int,
    ) -> None:
        await (
            cls._redis_client()
            .zremrangebyscore(
                cls._key(user_id),
                "-inf",
                time.time(),
            )
        )

    @classmethod
    async def touch(
        cls,
        *,
        user_id: int,
        connection_id: str,
    ) -> float:
        expires_at = (
            time.time()
            + cls.LEASE_SECONDS
        )

        if cls._uses_memory_backend():
            cls._memory_prune(
                user_id=user_id,
            )

            leases = (
                cls._memory_leases
                .setdefault(
                    user_id,
                    {},
                )
            )

            leases[
                connection_id
            ] = expires_at

            return expires_at

        client = cls._redis_client()
        key = cls._key(user_id)

        await cls._redis_prune(
            user_id=user_id,
        )

        await client.zadd(
            key,
            {
                connection_id:
                    expires_at,
            },
        )
        await client.expire(
            key,
            cls.KEY_TTL_SECONDS,
        )

        return expires_at

    @classmethod
    async def remove(
        cls,
        *,
        user_id: int,
        connection_id: str,
    ) -> float | None:
        if cls._uses_memory_backend():
            cls._memory_prune(
                user_id=user_id,
            )

            leases = (
                cls._memory_leases.get(
                    user_id,
                    {},
                )
            )
            leases.pop(
                connection_id,
                None,
            )

            cls._memory_prune(
                user_id=user_id,
            )

            remaining = (
                cls._memory_leases.get(
                    user_id,
                    {},
                )
            )

            return (
                max(remaining.values())
                if remaining
                else None
            )

        client = cls._redis_client()
        key = cls._key(user_id)

        await client.zrem(
            key,
            connection_id,
        )

        await cls._redis_prune(
            user_id=user_id,
        )

        result = await client.zrange(
            key,
            0,
            -1,
            withscores=True,
        )

        if not result:
            await client.delete(key)
            return None

        return max(
            score
            for _, score
            in result
        )

    @classmethod
    async def online_until(
        cls,
        *,
        user_id: int,
    ) -> float | None:
        if cls._uses_memory_backend():
            cls._memory_prune(
                user_id=user_id,
            )

            leases = (
                cls._memory_leases.get(
                    user_id,
                    {},
                )
            )

            return (
                max(leases.values())
                if leases
                else None
            )

        client = cls._redis_client()
        key = cls._key(user_id)

        await cls._redis_prune(
            user_id=user_id,
        )

        result = await client.zrange(
            key,
            0,
            -1,
            withscores=True,
        )

        if not result:
            return None

        return max(
            score
            for _, score
            in result
        )
