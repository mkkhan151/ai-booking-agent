'use client';

import { useState, useEffect, useCallback, useRef } from "react";

export interface Message {
    role: 'user' | 'agent';
    text: string;
}

export function useChatSocket(wsUrl: string, sessionId: string) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout>(null);
    const reconnectAttemptsRef = useRef(0);
    const maxReconnectAttempts = 5;

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return;
        }

        setIsConnecting(true);
        const ws = new WebSocket(`${wsUrl}/${sessionId}`);

        ws.onopen = () => {
            console.log('WebSocket connected');
            setIsConnected(true);
            setIsConnecting(false);
            reconnectAttemptsRef.current = 0;
        };

        ws.onmessage = (event) => {
            try {
                const agentMessage = event.data;

                // add agent's response to messages
                setMessages((prev) => [...prev, { role: 'agent', text: agentMessage }]);
                setIsLoading(false);
            } catch (error) {
                console.error('Error parsing message:', error);
                setIsLoading(false);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            setIsConnecting(false);
            setIsLoading(false);
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
            setIsConnected(false);
            setIsConnecting(false);
            setIsLoading(false);
            wsRef.current = null;

            // Auto-reconnect with exponential backoff
            if (reconnectAttemptsRef.current < maxReconnectAttempts) {
                const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
                console.log(`Reconnecting in ${delay}ms...`);

                reconnectTimeoutRef.current = setTimeout(() => {
                    reconnectAttemptsRef.current += 1;
                    connect();
                }, delay);
            } else {
                console.error('Max reconnection attempts reached');
            }
        };

        wsRef.current = ws;
    }, [wsUrl, sessionId]);

    useEffect(() => {
        connect();

        return () => {
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [connect]);

    const sendMessage = useCallback((text: string) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            console.error('WebSocket is not connected');
            return;
        }

        // Add user message to state
        setMessages((prev) => [...prev, { role: 'user', text }]);
        setIsLoading(true);

        // Send to server
        wsRef.current.send(text);
    }, []);

    const reconnect = useCallback(() => {
        reconnectAttemptsRef.current = 0;
        connect();
    }, [connect]);

    return {
        messages,
        isConnected,
        isConnecting,
        isLoading,
        sendMessage,
        reconnect,
    };
}