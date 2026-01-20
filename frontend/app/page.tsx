'use client';

import { useState, useEffect, useRef } from 'react';
import { useChatSocket } from './hooks/useChatSocket';

export default function Home() {
    const [inputMessage, setInputMessage] = useState('');
    const [sessionId] = useState(() => `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const wsUrl = `ws://${process.env.NEXT_PUBLIC_BACKEN_URL}/ws` || 'ws://localhost:8000/ws';
    const { messages, isConnected, isConnecting, sendMessage, reconnect } = useChatSocket(wsUrl, sessionId);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSendMessage = (e: React.FormEvent) => {
        e.preventDefault();
        if (inputMessage.trim() && isConnected) {
            sendMessage(inputMessage.trim());
            setInputMessage('');
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage(e);
        }
    };

    return (
        <div className="flex flex-col h-screen bg-linear-to-br from-blue-50 to-indigo-100">
            {/* Header */}
            <div className="bg-white shadow-md px-6 py-4 border-b border-gray-200">
                <div className="max-w-4xl mx-auto flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-800">AI Booking Agent</h1>
                        <p className="text-sm text-gray-600">Book time slots between 9 AM - 5 PM</p>
                    </div>
                    <div className="flex items-center gap-2">
                        {isConnecting && (
                            <div className="flex items-center gap-2 text-yellow-600">
                                <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
                                <span className="text-sm font-medium">Connecting...</span>
                            </div>
                        )}
                        {isConnected && !isConnecting && (
                            <div className="flex items-center gap-2 text-green-600">
                                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                                <span className="text-sm font-medium">Connected</span>
                            </div>
                        )}
                        {!isConnected && !isConnecting && (
                            <div className="flex items-center gap-2">
                                <div className="flex items-center gap-2 text-red-600">
                                    <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                                    <span className="text-sm font-medium">Disconnected</span>
                                </div>
                                <button
                                    onClick={reconnect}
                                    className="ml-2 px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
                                >
                                    Reconnect
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Messages Container */}
            <div className="flex-1 overflow-y-auto px-4 py-6">
                <div className="max-w-4xl mx-auto space-y-4">
                    {messages.length === 0 && (
                        <div className="text-center py-12">
                            <div className="inline-block p-4 bg-white rounded-full shadow-md mb-4">
                                <svg className="w-12 h-12 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                                </svg>
                            </div>
                            <h2 className="text-xl font-semibold text-gray-700 mb-2">Welcome to AI Booking Agent!</h2>
                            <p className="text-gray-500">Start a conversation to book your time slot</p>
                        </div>
                    )}

                    {messages.map((message, index) => (
                        <div
                            key={index}
                            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-xs md:max-w-md lg:max-w-lg xl:max-w-xl px-4 py-3 rounded-2xl shadow-md ${message.role === 'user'
                                    ? 'bg-blue-500 text-white rounded-br-none'
                                    : 'bg-white text-gray-800 rounded-bl-none'
                                    }`}
                            >
                                <div className="text-xs font-semibold mb-1 opacity-70">
                                    {message.role === 'user' ? 'You' : 'Agent'}
                                </div>
                                <div className="whitespace-pre-wrap wrap-break-word">{message.text}</div>
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input Form */}
            <div className="bg-white border-t border-gray-200 px-4 py-4 shadow-lg">
                <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto">
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={inputMessage}
                            onChange={(e) => setInputMessage(e.target.value)}
                            onKeyUp={handleKeyPress}
                            placeholder={isConnected ? "Type your message..." : "Connecting..."}
                            disabled={!isConnected}
                            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                        />
                        <button
                            type="submit"
                            disabled={!isConnected || !inputMessage.trim()}
                            className="px-6 py-3 bg-blue-500 text-white font-medium rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                        >
                            Send
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
