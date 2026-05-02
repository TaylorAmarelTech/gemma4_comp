// React component for embedding Duecare chat into any React app.
//
// This is a single-file reference implementation — drop into any
// React 18+ codebase and it works. For a published npm package
// `@duecare/chat-widget`, see the publishing notes at
// `docs/embedding_guide.md` §3.
//
// Usage:
//   import { DuecareChat } from './DuecareChat';
//
//   export default function Page() {
//     return (
//       <div style={{ height: 600 }}>
//         <DuecareChat
//           apiUrl="https://your-duecare-deploy.example.com"
//           toggles={{ grep: true, rag: true, tools: true }}
//           onResponse={(msg) => console.log('Gemma:', msg)}
//         />
//       </div>
//     );
//   }

import React, {
    useCallback, useEffect, useRef, useState,
} from 'react';

interface ChatMessage {
    role: 'user' | 'assistant';
    text: string;
    meta?: string;
    error?: boolean;
}

interface HarnessToggles {
    persona?: boolean;
    grep?: boolean;
    rag?: boolean;
    tools?: boolean;
    persona_text?: string | null;
}

export interface DuecareChatProps {
    apiUrl: string;
    toggles?: HarnessToggles;
    personaText?: string;
    placeholder?: string;
    suggestedPrompts?: string[];
    maxNewTokens?: number;
    theme?: 'light' | 'dark';
    onResponse?: (text: string) => void;
    onError?: (err: Error) => void;
}

const DEFAULT_PROMPTS = [
    'Is a ₱50,000 "training fee" legal for PH→HK domestic worker deployment?',
    'My recruiter is keeping my passport "for safekeeping". Is that allowed?',
    'My loan APR is 68% per year. Is this legal in Hong Kong?',
];

export function DuecareChat(props: DuecareChatProps): React.ReactElement {
    const {
        apiUrl,
        toggles = { persona: false, grep: true, rag: true, tools: true },
        personaText,
        placeholder = 'Ask about a fee, contract, or recruiter message...',
        suggestedPrompts = DEFAULT_PROMPTS,
        maxNewTokens = 1024,
        theme = 'light',
        onResponse,
        onError,
    } = props;

    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [streamingText, setStreamingText] = useState<string | null>(null);
    const [input, setInput] = useState('');
    const [inFlight, setInFlight] = useState(false);
    const listRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (listRef.current) {
            listRef.current.scrollTop = listRef.current.scrollHeight;
        }
    }, [messages.length, streamingText]);

    const palette = theme === 'dark' ? {
        bg: '#0f172a', surface: '#1e293b', surfaceAlt: '#334155',
        text: '#e2e8f0', muted: '#94a3b8', accent: '#60a5fa',
        userBubble: '#1e3a8a', userBubbleText: '#dbeafe',
        asstBubble: '#334155', asstBubbleText: '#e2e8f0',
        border: '#334155',
    } : {
        bg: '#ffffff', surface: '#f8fafc', surfaceAlt: '#f1f5f9',
        text: '#0f172a', muted: '#64748b', accent: '#2563eb',
        userBubble: '#dbeafe', userBubbleText: '#1e3a8a',
        asstBubble: '#f1f5f9', asstBubbleText: '#0f172a',
        border: '#e2e8f0',
    };

    const send = useCallback(async (textOverride?: string) => {
        const text = (textOverride ?? input).trim();
        if (!text || inFlight) return;
        setInput('');
        setInFlight(true);
        setStreamingText('');

        const newMessages: ChatMessage[] = [
            ...messages,
            { role: 'user', text },
        ];
        setMessages(newMessages);

        try {
            const r = await fetch(`${apiUrl}/api/chat/send`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: newMessages.map((m) => ({
                        role: m.role,
                        content: [{ type: 'text', text: m.text }],
                    })),
                    generation: { max_new_tokens: maxNewTokens },
                    toggles: { ...toggles, persona_text: personaText ?? null },
                }),
            });
            if (!r.ok) {
                const errTxt = await r.text();
                throw new Error(`HTTP ${r.status}: ${errTxt.slice(0, 200)}`);
            }
            const reader = r.body!.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let finalResult: any = null;
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                let sep;
                while ((sep = buffer.indexOf('\n\n')) !== -1) {
                    const event = buffer.slice(0, sep);
                    buffer = buffer.slice(sep + 2);
                    if (event.startsWith('data:')) {
                        try {
                            finalResult = JSON.parse(event.slice(5).trim());
                        } catch (e) { /* skip malformed */ }
                    }
                }
            }
            if (!finalResult) throw new Error('stream ended without result');
            if (finalResult.error) throw new Error(finalResult.error);
            const reply = finalResult.response || '(empty)';
            setStreamingText(null);
            setMessages((prev) => [
                ...prev,
                {
                    role: 'assistant',
                    text: reply,
                    meta: `${finalResult.elapsed_ms || '?'} ms · ${finalResult.model_info?.display || 'gemma'}`,
                },
            ]);
            onResponse?.(reply);
        } catch (err: unknown) {
            const e = err as Error;
            setStreamingText(null);
            setMessages((prev) => [
                ...prev,
                { role: 'assistant', text: `⚠ ${e.message || e}`, error: true },
            ]);
            onError?.(e);
        } finally {
            setInFlight(false);
        }
    }, [apiUrl, input, inFlight, messages, toggles, personaText, maxNewTokens, onResponse, onError]);

    return (
        <div style={{
            display: 'flex', flexDirection: 'column',
            background: palette.bg, color: palette.text,
            fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
            border: `1px solid ${palette.border}`,
            borderRadius: 12, overflow: 'hidden',
            height: '100%', minHeight: 420,
        }}>
            <div style={{
                padding: '10px 14px', background: palette.surface,
                borderBottom: `1px solid ${palette.border}`,
                fontSize: 13, color: palette.muted,
            }}>
                <strong style={{ color: palette.text }}>Duecare chat</strong>
                <span> · powered by Gemma 4 + safety harness</span>
            </div>
            <div ref={listRef} style={{
                flex: '1 1 auto', overflowY: 'auto', padding: 14,
                display: 'flex', flexDirection: 'column', gap: 10,
            }}>
                {messages.length === 0 && !streamingText && (
                    <div style={{ color: palette.muted, textAlign: 'center', padding: '30px 20px' }}>
                        <div style={{ fontSize: 15, fontWeight: 600, color: palette.text, marginBottom: 6 }}>
                            Ask anything about your migration journey
                        </div>
                        <div style={{ fontSize: 13, marginBottom: 14 }}>
                            I cite specific statutes, ILO conventions, and the right NGO/regulator
                            hotline for your corridor. I won't tell you what to do — you choose.
                        </div>
                        {suggestedPrompts.map((sp) => (
                            <button key={sp} onClick={() => send(sp)} style={{
                                display: 'block', width: '100%', margin: '6px 0',
                                padding: '10px 12px', background: palette.surfaceAlt,
                                color: palette.text, border: `1px solid ${palette.border}`,
                                borderRadius: 8, cursor: 'pointer', fontSize: 13,
                                textAlign: 'left',
                            }}>{sp}</button>
                        ))}
                    </div>
                )}
                {messages.map((m, i) => (
                    <Bubble key={i} message={m} palette={palette} />
                ))}
                {streamingText !== null && (
                    <Bubble message={{ role: 'assistant', text: streamingText || '… thinking …' }}
                            palette={palette} />
                )}
            </div>
            <div style={{
                padding: 10, background: palette.surface,
                borderTop: `1px solid ${palette.border}`,
                display: 'flex', gap: 8,
            }}>
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            send();
                        }
                    }}
                    placeholder={placeholder}
                    rows={2}
                    style={{
                        flex: '1 1 auto', background: palette.bg, color: palette.text,
                        border: `1px solid ${palette.border}`, borderRadius: 8,
                        padding: '8px 10px', fontSize: 14, resize: 'vertical',
                        minHeight: 40, fontFamily: 'inherit',
                    }}
                />
                <button onClick={() => send()} disabled={!input.trim() || inFlight} style={{
                    background: palette.accent, color: '#fff', border: 'none',
                    borderRadius: 8, padding: '0 16px', cursor: 'pointer',
                    fontWeight: 600, fontSize: 14,
                    opacity: !input.trim() || inFlight ? 0.6 : 1,
                }}>{inFlight ? '…' : 'Send'}</button>
            </div>
        </div>
    );
}

function Bubble({
    message, palette,
}: { message: ChatMessage, palette: any }): React.ReactElement {
    const isUser = message.role === 'user';
    return (
        <div style={{
            alignSelf: isUser ? 'flex-end' : 'flex-start',
            maxWidth: '80%',
            padding: '10px 12px',
            borderRadius: 14,
            background: isUser ? palette.userBubble : palette.asstBubble,
            color: message.error ? '#ef4444'
                : (isUser ? palette.userBubbleText : palette.asstBubbleText),
            fontSize: 14, lineHeight: 1.45,
            whiteSpace: 'pre-wrap', wordBreak: 'break-word',
        }}>
            {message.text}
            {message.meta && (
                <div style={{ marginTop: 6, fontSize: 11, color: palette.muted }}>
                    {message.meta}
                </div>
            )}
        </div>
    );
}
