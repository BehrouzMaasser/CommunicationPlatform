(() => {
    "use strict";

    const body = document.body;
    const activitySummaryUrl =
        body.dataset.activitySummaryUrl;
    const realtimePath =
        body.dataset.realtimeUrl;

    if (!activitySummaryUrl || !realtimePath) {
        return;
    }

    const activityEventTypes = new Set([
        "connection.connected",
        "message.created",
        "message.read",
        "friend_request.created",
        "friend_request.accepted",
        "friend_request.rejected",
        "friend_request.cancelled",
        "group_invitation.created",
        "group_invitation.accepted",
        "group_invitation.rejected",
        "group_invitation.cancelled",
        "group.member_added",
        "group.member_removed",
        "group.member_left",
        "group.deleted",
    ]);

    let socket = null;
    let reconnectTimer = null;
    let reconnectAttempt = 0;
    let heartbeatTimer = null;
    let refreshTimer = null;
    let refreshInFlight = false;
    let refreshAgain = false;
    let stopped = false;

    function safeCount(value) {
        const number = Number(value);

        if (!Number.isFinite(number)) {
            return 0;
        }

        return Math.max(0, Math.trunc(number));
    }

    function displayCount(count) {
        return count > 99
            ? "99+"
            : String(count);
    }

    function updateBadges(
        kind,
        count,
        ariaLabel,
        title = ariaLabel,
    ) {
        const badges = document.querySelectorAll(
            `[data-activity-badge="${kind}"]`,
        );

        for (const badge of badges) {
            badge.textContent =
                count > 0
                    ? displayCount(count)
                    : "";

            badge.classList.toggle(
                "d-none",
                count === 0,
            );

            if (count > 0) {
                badge.setAttribute(
                    "aria-label",
                    ariaLabel,
                );
                badge.setAttribute(
                    "title",
                    title,
                );
            } else {
                badge.removeAttribute(
                    "aria-label",
                );
                badge.removeAttribute(
                    "title",
                );
            }
        }
    }

    function applySummary(summary) {
        const pendingFriendRequests =
            safeCount(
                summary.pending_friend_requests,
            );
        const unreadDirectMessages =
            safeCount(
                summary.unread_direct_messages,
            );
        const unreadGroupMessages =
            safeCount(
                summary.unread_group_messages,
            );
        const pendingGroupInvitations =
            safeCount(
                summary.pending_group_invitations,
            );
        const groupAttention =
            unreadGroupMessages
            + pendingGroupInvitations;

        updateBadges(
            "friends",
            pendingFriendRequests,
            `${pendingFriendRequests} pending friend requests`,
        );

        updateBadges(
            "messages",
            unreadDirectMessages,
            `${unreadDirectMessages} unread direct messages`,
        );

        updateBadges(
            "groups",
            groupAttention,
            `${groupAttention} group items needing attention`,
            `${unreadGroupMessages} unread group messages · ${pendingGroupInvitations} pending group invitations`,
        );
    }

    async function refreshActivity() {
        refreshTimer = null;

        if (stopped) {
            return;
        }

        if (refreshInFlight) {
            refreshAgain = true;
            return;
        }

        refreshInFlight = true;

        try {
            const response = await fetch(
                activitySummaryUrl,
                {
                    method: "GET",
                    credentials: "same-origin",
                    headers: {
                        Accept: "application/json",
                    },
                    cache: "no-store",
                },
            );

            if (
                response.status === 401
                || response.status === 403
            ) {
                stopRealtime();
                return;
            }

            if (!response.ok) {
                return;
            }

            const summary =
                await response.json();

            applySummary(summary);
        } catch {
            // Realtime chrome is best-effort. The next event/reconnect
            // reconciles again from the durable activity summary.
        } finally {
            refreshInFlight = false;

            if (refreshAgain && !stopped) {
                refreshAgain = false;
                scheduleRefresh(0);
            }
        }
    }

    function scheduleRefresh(delay = 150) {
        if (stopped) {
            return;
        }

        if (refreshTimer !== null) {
            window.clearTimeout(
                refreshTimer,
            );
        }

        refreshTimer =
            window.setTimeout(
                refreshActivity,
                delay,
            );
    }

    function requestId() {
        if (
            window.crypto
            && typeof window.crypto.randomUUID
                === "function"
        ) {
            return window.crypto.randomUUID();
        }

        return (
            `${Date.now()}-`
            + Math.random()
                .toString(16)
                .slice(2)
        );
    }

    function sendHeartbeat() {
        if (
            !socket
            || socket.readyState
                !== WebSocket.OPEN
        ) {
            return;
        }

        socket.send(
            JSON.stringify({
                type: "presence.heartbeat",
                request_id: requestId(),
                payload: {},
            }),
        );
    }

    function stopHeartbeat() {
        if (heartbeatTimer === null) {
            return;
        }

        window.clearInterval(
            heartbeatTimer,
        );
        heartbeatTimer = null;
    }

    function startHeartbeat() {
        stopHeartbeat();
        sendHeartbeat();

        heartbeatTimer =
            window.setInterval(
                sendHeartbeat,
                25000,
            );
    }

    function websocketUrl() {
        const url = new URL(
            realtimePath,
            window.location.origin,
        );

        url.protocol =
            window.location.protocol
                === "https:"
                ? "wss:"
                : "ws:";

        return url.toString();
    }

    function scheduleReconnect() {
        if (
            stopped
            || reconnectTimer !== null
        ) {
            return;
        }

        const delay = Math.min(
            1000 * (2 ** reconnectAttempt),
            10000,
        );

        reconnectAttempt += 1;

        reconnectTimer =
            window.setTimeout(
                () => {
                    reconnectTimer = null;
                    connect();
                },
                delay,
            );
    }

    function connect() {
        if (
            stopped
            || (
                socket
                && (
                    socket.readyState
                        === WebSocket.OPEN
                    || socket.readyState
                        === WebSocket.CONNECTING
                )
            )
        ) {
            return;
        }

        const nextSocket =
            new WebSocket(
                websocketUrl(),
            );

        socket = nextSocket;

        nextSocket.addEventListener(
            "open",
            () => {
                if (socket !== nextSocket) {
                    nextSocket.close();
                    return;
                }

                reconnectAttempt = 0;
                startHeartbeat();
                scheduleRefresh(0);
            },
        );

        nextSocket.addEventListener(
            "message",
            (message) => {
                if (
                    socket !== nextSocket
                    || typeof message.data
                        !== "string"
                ) {
                    return;
                }

                let event;

                try {
                    event =
                        JSON.parse(
                            message.data,
                        );
                } catch {
                    return;
                }

                if (
                    !event
                    || typeof event.type
                        !== "string"
                    || !activityEventTypes.has(
                        event.type,
                    )
                ) {
                    return;
                }

                scheduleRefresh();
            },
        );

        nextSocket.addEventListener(
            "close",
            (event) => {
                if (socket !== nextSocket) {
                    return;
                }

                socket = null;
                stopHeartbeat();

                if (event.code === 4401) {
                    stopped = true;
                    return;
                }

                scheduleReconnect();
            },
        );

        nextSocket.addEventListener(
            "error",
            () => {
                nextSocket.close();
            },
        );
    }

    function stopRealtime() {
        stopped = true;
        stopHeartbeat();

        if (refreshTimer !== null) {
            window.clearTimeout(
                refreshTimer,
            );
            refreshTimer = null;
        }

        if (reconnectTimer !== null) {
            window.clearTimeout(
                reconnectTimer,
            );
            reconnectTimer = null;
        }

        const currentSocket = socket;
        socket = null;

        if (currentSocket) {
            currentSocket.close();
        }
    }

    window.addEventListener(
        "pagehide",
        stopRealtime,
        { once: true },
    );

    connect();
})();
