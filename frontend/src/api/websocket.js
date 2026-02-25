/**
 * SmartV2X-CP Ultra — WebSocket Client
 * Manages WebSocket connection for live vehicle updates.
 */

const getWsUrl = () => {
    const envUrl = import.meta.env.VITE_WS_URL;
    if (envUrl && (envUrl.startsWith('ws://') || envUrl.startsWith('wss://'))) {
        return envUrl;
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}${envUrl || '/ws/live'}`;
};

const WS_URL = getWsUrl();

export class V2XWebSocket {
    constructor(onMessage, onStatusChange) {
        this.onMessage = onMessage;
        this.onStatusChange = onStatusChange;
        this.ws = null;
        this.reconnectTimer = null;
        this.reconnectDelay = 1000;
        this.maxDelay = 30000;
    }

    connect() {
        try {
            this.ws = new WebSocket(WS_URL);

            this.ws.onopen = () => {
                console.log('[WS] Connected');
                this.onStatusChange(true);
                this.reconnectDelay = 1000;
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.onMessage(data);
                } catch (err) {
                    console.warn('[WS] Parse error:', err);
                }
            };

            this.ws.onclose = () => {
                console.log('[WS] Disconnected');
                this.onStatusChange(false);
                this._scheduleReconnect();
            };

            this.ws.onerror = (err) => {
                console.error('[WS] Error:', err);
                this.onStatusChange(false);
            };
        } catch (err) {
            console.error('[WS] Connection error:', err);
            this._scheduleReconnect();
        }
    }

    _scheduleReconnect() {
        if (this.reconnectTimer) return;
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxDelay);
            console.log(`[WS] Reconnecting in ${this.reconnectDelay}ms...`);
            this.connect();
        }, this.reconnectDelay);
    }

    disconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }
}
