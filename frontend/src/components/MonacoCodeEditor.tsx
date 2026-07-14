import { useEffect, useRef } from 'react'
import Editor, { type OnMount } from '@monaco-editor/react'
import type { editor as MonacoEditor } from 'monaco-editor'

interface Props {
  value: string
  onChange?: (value: string) => void
  language?: string
  theme: 'dark' | 'light' | 'system'
  height?: number | string
  readOnly?: boolean
  scrollToEnd?: boolean
  scrollToLine?: number | null
}

function resolveMonacoTheme(theme: Props['theme']): string {
  if (theme === 'light') return 'vs'
  if (theme === 'dark') return 'vs-dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'vs-dark' : 'vs'
}

function profileToLanguage(profile: string): string {
  if (profile.startsWith('python') || profile === 'adb_shell') return 'python'
  if (profile.startsWith('java')) return 'java'
  if (profile.startsWith('javascript')) return 'javascript'
  return 'python'
}

export default function MonacoCodeEditor({
  value,
  onChange,
  language = 'python',
  theme,
  height = '100%',
  readOnly = false,
  scrollToEnd = false,
  scrollToLine = null,
}: Props) {
  const monacoTheme = resolveMonacoTheme(theme)
  const lang = language.includes('_') ? profileToLanguage(language) : language
  const editorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null)

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
    editorRef.current = ed
    ed.updateOptions({ readOnly })
    if (scrollToEnd && value) {
      const line = ed.getModel()?.getLineCount() ?? 1
      ed.revealLine(line)
    }
  }

  useEffect(() => {
    if (!scrollToEnd || !editorRef.current || !value) return
    const line = editorRef.current.getModel()?.getLineCount() ?? 1
    editorRef.current.revealLine(line)
  }, [value, scrollToEnd])

  useEffect(() => {
    if (!scrollToLine || !editorRef.current) return
    editorRef.current.revealLineInCenter(scrollToLine)
    editorRef.current.setSelection({
      startLineNumber: scrollToLine,
      startColumn: 1,
      endLineNumber: scrollToLine,
      endColumn: 1,
    })
  }, [scrollToLine])

  return (
    <div className="monaco-code-editor">
      <Editor
        height={height}
        language={lang}
        theme={monacoTheme}
        value={value}
        onChange={(v) => onChange?.(v ?? '')}
        onMount={handleMount}
        options={{
          readOnly,
          minimap: { enabled: true },
          lineNumbers: 'on',
          folding: true,
          wordWrap: 'on',
          tabSize: 4,
          insertSpaces: true,
          automaticLayout: true,
          scrollBeyondLastLine: false,
          formatOnPaste: true,
          fontSize: 13,
          fontFamily: 'JetBrains Mono, Fira Code, Consolas, monospace',
          padding: { top: 8, bottom: 8 },
        }}
      />
    </div>
  )
}
