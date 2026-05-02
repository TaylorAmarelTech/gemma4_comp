/*
 * Duecare Chat Widget — embeddable single-file JS.
 *
 * Drops a working chat UI into any page that wants to call a
 * deployed Duecare REST API. Mirrors the chat-playground UX (message
 * bubbles, harness-trace metadata, suggested prompts) without any
 * framework dependency.
 *
 * Usage:
 *   <div id="duecare-chat"></div>
 *   <script src="duecare-widget.js"></script>
 *   <script>
 *     Duecare.mount('#duecare-chat', {
 *       apiUrl: 'https://your-duecare-deploy.example.com',
 *       toggles: { grep: true, rag: true, tools: true },
 *     });
 *   </script>
 *
 * Privacy: every message ships in `toggles.custom_*` fields per the
 * Duecare API; the widget itself stores nothing. Customizations live
 * in `localStorage` under `duecare_widget_custom_*` keys.
 *
 * Source-of-truth: this file. Build to npm with: `npm publish` after
 * `package.json` is added (planned).
 */
(function () {
    'use strict';

    const VERSION = '0.5.0';

    function el(tag, attrs, children) {
        const e = document.createElement(tag);
        if (attrs) {
            for (const [k, v] of Object.entries(attrs)) {
                if (k === 'style' && typeof v === 'object') {
                    Object.assign(e.style, v);
                } else if (k.startsWith('on') && typeof v === 'function') {
                    e.addEventListener(k.slice(2).toLowerCase(), v);
                } else if (k === 'className') {
                    e.className = v;
                } else {
                    e.setAttribute(k, v);
                }
            }
        }
        if (children) {
            for (const c of [].concat(children)) {
                if (typeof c === 'string') e.appendChild(document.createTextNode(c));
                else if (c) e.appendChild(c);
            }
        }
        return e;
    }

    function mount(selectorOrEl, options) {
        const root = typeof selectorOrEl === 'string'
            ? document.querySelector(selectorOrEl)
            : selectorOrEl;
        if (!root) throw new Error(`Duecare.mount: target not found: ${selectorOrEl}`);

        const opts = Object.assign({
            apiUrl: 'http://localhost:8080',
            toggles: { persona: false, grep: true, rag: true, tools: true },
            personaText: null,
            theme: 'light',
            placeholder: 'Ask about a fee, contract, or recruiter message...',
            suggestedPrompts: [
                'Is a ₱50,000 "training fee" legal for PH→HK domestic worker deployment?',
                'My recruiter is keeping my passport "for safekeeping". Is that allowed?',
                'My loan APR is 68% per year. Is this legal in Hong Kong?',
            ],
            maxNewTokens: 1024,
            onResponse: null,                 // (msg) => {}
            onError: null,                    // (err) => {}
        }, options || {});

        const messages = [];
        const isDark = opts.theme === 'dark';
        const palette = isDark ? {
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

        // Layout
        Object.assign(root.style, {
            display: 'flex',
            flexDirection: 'column',
            background: palette.bg,
            color: palette.text,
            fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
            border: `1px solid ${palette.border}`,
            borderRadius: '12px',
            overflow: 'hidden',
            height: '100%',
            minHeight: '420px',
        });

        const header = el('div', {
            style: {
                padding: '10px 14px',
                background: palette.surface,
                borderBottom: `1px solid ${palette.border}`,
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                fontSize: '13px',
                color: palette.muted,
            },
        }, [
            el('strong', { style: { color: palette.text } }, 'Duecare chat'),
            el('span', null, ' · '),
            el('span', null, `v${VERSION}`),
        ]);

        const chatList = el('div', {
            style: {
                flex: '1 1 auto',
                overflowY: 'auto',
                padding: '14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
            },
        });

        const empty = el('div', {
            style: {
                color: palette.muted,
                textAlign: 'center',
                padding: '30px 20px',
            },
        }, [
            el('div', { style: { fontSize: '15px', fontWeight: '600', color: palette.text, marginBottom: '6px' } },
                'Ask anything about your migration journey'),
            el('div', { style: { fontSize: '13px', marginBottom: '14px' } },
                'I cite specific statutes, ILO conventions, and the right NGO/regulator hotline for your corridor. I won\'t tell you what to do — you choose.'),
        ]);
        for (const sp of opts.suggestedPrompts) {
            empty.appendChild(el('button', {
                onclick: () => { input.value = sp; send(); },
                style: {
                    display: 'block',
                    width: '100%',
                    margin: '6px 0',
                    padding: '10px 12px',
                    background: palette.surfaceAlt,
                    color: palette.text,
                    border: `1px solid ${palette.border}`,
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontSize: '13px',
                    textAlign: 'left',
                },
            }, sp));
        }
        chatList.appendChild(empty);

        const composer = el('div', {
            style: {
                padding: '10px',
                background: palette.surface,
                borderTop: `1px solid ${palette.border}`,
                display: 'flex',
                gap: '8px',
            },
        });
        const input = el('textarea', {
            placeholder: opts.placeholder,
            rows: '2',
            style: {
                flex: '1 1 auto',
                background: palette.bg,
                color: palette.text,
                border: `1px solid ${palette.border}`,
                borderRadius: '8px',
                padding: '8px 10px',
                fontSize: '14px',
                resize: 'vertical',
                minHeight: '40px',
                fontFamily: 'inherit',
            },
        });
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
            }
        });
        const sendBtn = el('button', {
            onclick: send,
            style: {
                background: palette.accent,
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                padding: '0 16px',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '14px',
            },
        }, 'Send');
        composer.appendChild(input);
        composer.appendChild(sendBtn);

        root.appendChild(header);
        root.appendChild(chatList);
        root.appendChild(composer);

        function bubbleFor(role, text, meta) {
            const isUser = role === 'user';
            const bubble = el('div', {
                style: {
                    alignSelf: isUser ? 'flex-end' : 'flex-start',
                    maxWidth: '80%',
                    padding: '10px 12px',
                    borderRadius: '14px',
                    background: isUser ? palette.userBubble : palette.asstBubble,
                    color: isUser ? palette.userBubbleText : palette.asstBubbleText,
                    fontSize: '14px',
                    lineHeight: '1.45',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                },
            }, text);
            if (meta) {
                bubble.appendChild(el('div', {
                    style: { marginTop: '6px', fontSize: '11px', color: palette.muted },
                }, meta));
            }
            return bubble;
        }

        function appendMessage(role, text, meta) {
            if (chatList.contains(empty)) chatList.removeChild(empty);
            const b = bubbleFor(role, text, meta);
            chatList.appendChild(b);
            chatList.scrollTop = chatList.scrollHeight;
            return b;
        }

        async function send() {
            const text = input.value.trim();
            if (!text) return;
            input.value = '';
            sendBtn.disabled = true;
            sendBtn.textContent = '…';
            appendMessage('user', text);
            const placeholder = appendMessage('assistant', '… thinking …', null);

            messages.push({ role: 'user', content: [{ type: 'text', text }] });

            try {
                const r = await fetch(`${opts.apiUrl}/api/chat/send`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        messages,
                        generation: { max_new_tokens: opts.maxNewTokens },
                        toggles: Object.assign({
                            persona_text: opts.personaText,
                        }, opts.toggles),
                    }),
                });
                if (!r.ok) {
                    const errTxt = await r.text();
                    throw new Error(`HTTP ${r.status}: ${errTxt.slice(0, 200)}`);
                }
                // Parse SSE stream
                const reader = r.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let finalResult = null;
                const tStart = Date.now();
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });
                    let sep;
                    while ((sep = buffer.indexOf('\n\n')) !== -1) {
                        const event = buffer.slice(0, sep);
                        buffer = buffer.slice(sep + 2);
                        if (event.startsWith(':')) {
                            const elapsed = ((Date.now() - tStart) / 1000).toFixed(0);
                            placeholder.textContent = `… generating (${elapsed}s)`;
                        } else if (event.startsWith('data:')) {
                            try {
                                finalResult = JSON.parse(event.slice(5).trim());
                            } catch (e) { /* skip */ }
                        }
                    }
                }
                if (!finalResult) throw new Error('stream ended without a result event');
                if (finalResult.error) throw new Error(finalResult.error);
                const reply = finalResult.response || '(empty response)';
                placeholder.textContent = reply;
                const meta = `${finalResult.elapsed_ms || '?'} ms · ${finalResult.model_info?.display || 'gemma'}`;
                placeholder.appendChild(el('div', {
                    style: { marginTop: '6px', fontSize: '11px', color: palette.muted },
                }, meta));
                messages.push({ role: 'assistant', content: [{ type: 'text', text: reply }] });
                if (opts.onResponse) opts.onResponse(reply);
            } catch (err) {
                placeholder.textContent = `⚠ Error: ${err.message || err}`;
                placeholder.style.color = '#ef4444';
                if (opts.onError) opts.onError(err);
            } finally {
                sendBtn.disabled = false;
                sendBtn.textContent = 'Send';
                input.focus();
            }
        }

        return {
            send,
            clear: () => {
                messages.length = 0;
                while (chatList.firstChild) chatList.removeChild(chatList.firstChild);
                chatList.appendChild(empty);
            },
            destroy: () => {
                while (root.firstChild) root.removeChild(root.firstChild);
            },
        };
    }

    window.Duecare = { mount, version: VERSION };
})();
