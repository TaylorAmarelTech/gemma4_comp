# Duecare Web Widget

Single-file embeddable chat — drop-in for any HTML page.

## Use

```html
<div id="duecare-chat" style="height:600px"></div>
<script src="https://cdn.jsdelivr.net/gh/TaylorAmarelTech/gemma4_comp@latest/examples/embedding/web-widget/duecare-widget.js"></script>
<script>
  Duecare.mount('#duecare-chat', {
    apiUrl: 'https://your-duecare-deploy.example.com',
    toggles: { grep: true, rag: true, tools: true },
  });
</script>
```

## Demo

Open `index.html` in a browser with a Duecare server running on
`http://localhost:8080`.

```bash
# in this directory
python -m http.server 9000
# open http://localhost:9000/
```

## Options

| Option | Default | Meaning |
|---|---|---|
| `apiUrl` | `http://localhost:8080` | URL of your Duecare deploy |
| `toggles` | `{persona:false, grep:true, rag:true, tools:true}` | Which harness layers to enable per message |
| `personaText` | `null` | Override the kernel-default persona |
| `theme` | `'light'` | `'light'` or `'dark'` |
| `placeholder` | "Ask about a fee..." | Composer placeholder |
| `suggestedPrompts` | 3 default OFW prompts | Shown in empty state; click to send |
| `maxNewTokens` | 1024 | Generation cap |
| `onResponse(msg)` | null | Callback fired on each Gemma response |
| `onError(err)` | null | Callback fired on any error |

## Privacy

The widget itself stores nothing. Messages ship per-request to the
configured `apiUrl`. Customizations (persona text, custom rules) live
in `localStorage` under keys prefixed with `duecare_widget_`.

For production embeds, run an auth proxy in front of the Duecare API
— the default Duecare server has no auth (per
`docs/embedding_guide.md` §"Privacy + security posture").

## License

MIT.
