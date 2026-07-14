import { useEffect } from 'react'
import Editor, { type OnMount } from '@monaco-editor/react'

export type LocatorEditorLanguage = 'xpath' | 'uiselector' | 'css' | 'java' | 'python' | 'javascript' | 'csharp' | 'ruby' | 'kotlin'

interface Props {
  value: string
  onChange: (value: string) => void
  language: LocatorEditorLanguage
  theme: 'dark' | 'light' | 'system'
  height?: number | string
  hasError?: boolean
  readOnly?: boolean
}

function resolveMonacoTheme(theme: Props['theme']): string {
  if (theme === 'light') return 'vs'
  if (theme === 'dark') return 'vs-dark'
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  return prefersDark ? 'vs-dark' : 'vs'
}

function monacoLanguage(lang: LocatorEditorLanguage): string {
  if (lang === 'xpath') return 'xml'
  if (lang === 'uiselector' || lang === 'java' || lang === 'kotlin') return 'java'
  if (lang === 'python') return 'python'
  if (lang === 'javascript') return 'javascript'
  if (lang === 'csharp') return 'csharp'
  if (lang === 'ruby') return 'ruby'
  return 'css'
}

export default function MonacoLocatorEditor({
  value, onChange, language, theme, height = 180, hasError, readOnly,
}: Props) {
  const monacoTheme = resolveMonacoTheme(theme)

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => {
      if (theme === 'system') {
        import('monaco-editor').then((monaco) => {
          monaco.editor.setTheme(mq.matches ? 'vs-dark' : 'vs')
        })
      }
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [theme])

  const handleMount: OnMount = (ed) => {
    ed.focus()
  }

  return (
    <div className={`monaco-locator-editor ${hasError ? 'has-error' : ''}`}>
      <Editor
        height={height}
        language={monacoLanguage(language)}
        theme={monacoTheme}
        value={value}
        onChange={(v) => onChange(v ?? '')}
        onMount={handleMount}
        options={{
          readOnly,
          minimap: { enabled: false },
          lineNumbers: 'on',
          folding: true,
          wordWrap: 'on',
          tabSize: 2,
          insertSpaces: true,
          automaticLayout: true,
          scrollBeyondLastLine: false,
          renderLineHighlight: 'all',
          bracketPairColorization: { enabled: true },
          matchBrackets: 'always',
          autoIndent: 'full',
          formatOnPaste: true,
          suggestOnTriggerCharacters: true,
          quickSuggestions: true,
          fontSize: 12,
          fontFamily: 'JetBrains Mono, Fira Code, Consolas, monospace',
          padding: { top: 8, bottom: 8 },
        }}
      />
    </div>
  )
}
