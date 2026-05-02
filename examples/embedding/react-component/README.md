# Duecare React Component

A drop-in React 18+ chat component that wraps a deployed Duecare API.

## Use

```bash
# Copy DuecareChat.tsx into your project, or symlink it
cp DuecareChat.tsx /path/to/your-app/src/components/
```

```tsx
import { DuecareChat } from './components/DuecareChat';

export default function Page() {
  return (
    <div style={{ height: 600 }}>
      <DuecareChat
        apiUrl="https://your-duecare-deploy.example.com"
        toggles={{ persona: true, grep: true, rag: true, tools: true }}
        theme="light"
        onResponse={(msg) => console.log('Gemma:', msg)}
      />
    </div>
  );
}
```

## Props

| Prop | Type | Default | Meaning |
|---|---|---|---|
| `apiUrl` | string | required | URL of your Duecare deploy |
| `toggles` | object | `{persona:false, grep:true, rag:true, tools:true}` | Which harness layers per message |
| `personaText` | string \| undefined | undefined | Override kernel persona |
| `placeholder` | string | "Ask about a fee..." | Composer placeholder |
| `suggestedPrompts` | string[] | 3 OFW defaults | Initial-state suggestions |
| `maxNewTokens` | number | 1024 | Generation cap |
| `theme` | `'light' \| 'dark'` | `'light'` | Color scheme |
| `onResponse` | (text: string) => void | undefined | Fired on each Gemma response |
| `onError` | (err: Error) => void | undefined | Fired on any error |

## Dependencies

React 18+. No other runtime dependencies (uses native `fetch` for SSE).

## Future: published npm package

To publish as `@duecare/chat-widget`:

```bash
mkdir react-package && cd react-package
npm init -y
# add the standard React-component package.json fields
npm install --save-peer react react-dom
# build with vite or tsup
npm publish --access public
```

The component is intentionally framework-light so it can be packaged
without complex toolchains.

## License

MIT.
