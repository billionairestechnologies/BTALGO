import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, CheckCircle, Loader2, Save, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { showToast } from '@/utils/toast'

const PROVIDERS = [
  { value: 'anthropic', label: 'Anthropic (Claude)', models: ['claude-sonnet-4-6', 'claude-opus-4-7', 'claude-haiku-4-5-20251001'] },
  { value: 'openai', label: 'OpenAI (GPT)', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'o1', 'o3-mini'] },
  { value: 'gemini', label: 'Google Gemini', models: ['gemini-2.0-flash', 'gemini-2.0-pro', 'gemini-1.5-flash', 'gemini-1.5-pro'] },
  { value: 'grok', label: 'xAI Grok', models: ['grok-3', 'grok-3-mini', 'grok-2'] },
  { value: 'openrouter', label: 'OpenRouter', models: ['anthropic/claude-sonnet-4-6', 'openai/gpt-4o', 'meta-llama/llama-3.3-70b-instruct', 'deepseek/deepseek-r1'] },
  { value: 'nexos', label: 'Nexos AI', models: ['nexos-pro', 'nexos-fast'] },
  { value: 'ollama', label: 'Ollama (Local)', models: ['llama3.2', 'llama3.1', 'mistral', 'qwen2.5', 'deepseek-r1'] },
]

interface Settings {
  provider: string
  model: string
  api_key: string
  base_url: string
  allow_orders: boolean
  allow_strategies: boolean
}

export default function BillySettings() {
  const navigate = useNavigate()
  const [settings, setSettings] = useState<Settings>({
    provider: 'anthropic',
    model: 'claude-sonnet-4-6',
    api_key: '',
    base_url: '',
    allow_orders: false,
    allow_strategies: true,
  })
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ status: string; message?: string } | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    fetch('/api/billy/settings', { credentials: 'include' })
      .then((r) => r.json())
      .then((data) => {
        if (data.provider) setSettings(data)
      })
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [])

  const currentProvider = PROVIDERS.find((p) => p.value === settings.provider)

  const handleSave = async () => {
    setIsSaving(true)
    try {
      const res = await fetch('/api/billy/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(settings),
      })
      if (!res.ok) throw new Error('Failed to save')
      showToast.success('Billy settings saved')
      setTestResult(null)
    } catch {
      showToast.error('Could not save Billy settings')
    } finally {
      setIsSaving(false)
    }
  }

  const handleTest = async () => {
    setIsTesting(true)
    setTestResult(null)
    try {
      const res = await fetch('/api/billy/status', { credentials: 'include' })
      const data = await res.json()
      setTestResult(data)
    } catch {
      setTestResult({ status: 'error', message: 'Network error' })
    } finally {
      setIsTesting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div>
          <h1 className="text-xl font-bold">Billy Settings</h1>
          <p className="text-sm text-muted-foreground">Configure your AI trading assistant</p>
        </div>
      </div>

      {/* Provider */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">AI Provider</CardTitle>
          <CardDescription>Select which AI provider Billy should use</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Provider</Label>
            <Select
              value={settings.provider}
              onValueChange={(v) => {
                const p = PROVIDERS.find((x) => x.value === v)
                setSettings((s) => ({ ...s, provider: v, model: p?.models[0] || '' }))
                setTestResult(null)
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PROVIDERS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Model</Label>
            <Select
              value={settings.model}
              onValueChange={(v) => setSettings((s) => ({ ...s, model: v }))}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {currentProvider?.models.map((m) => (
                  <SelectItem key={m} value={m}>
                    {m}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">You can type a custom model name in the field above</p>
          </div>
        </CardContent>
      </Card>

      {/* API Key */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Authentication</CardTitle>
          <CardDescription>
            {settings.provider === 'ollama'
              ? 'Ollama runs locally — no API key required'
              : 'Your API key is stored encrypted on the server'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {settings.provider !== 'ollama' && (
            <div className="space-y-2">
              <Label>API Key</Label>
              <Input
                type="password"
                placeholder="Enter your API key..."
                value={settings.api_key}
                onChange={(e) => setSettings((s) => ({ ...s, api_key: e.target.value }))}
              />
            </div>
          )}

          {(settings.provider === 'ollama' || settings.provider === 'openrouter') && (
            <div className="space-y-2">
              <Label>
                {settings.provider === 'ollama' ? 'Ollama Base URL' : 'Custom Base URL (optional)'}
              </Label>
              <Input
                placeholder={
                  settings.provider === 'ollama'
                    ? 'http://localhost:11434'
                    : 'Leave empty for default'
                }
                value={settings.base_url}
                onChange={(e) => setSettings((s) => ({ ...s, base_url: e.target.value }))}
              />
            </div>
          )}

          {/* Test connection */}
          <div className="flex items-center gap-3 pt-1">
            <Button variant="outline" size="sm" onClick={handleTest} disabled={isTesting}>
              {isTesting ? (
                <><Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />Testing...</>
              ) : (
                'Test Connection'
              )}
            </Button>
            {testResult && (
              <div className="flex items-center gap-1.5 text-sm">
                {testResult.status === 'ok' ? (
                  <><CheckCircle className="w-4 h-4 text-green-500" /><span className="text-green-600 dark:text-green-400">Connected</span></>
                ) : (
                  <><XCircle className="w-4 h-4 text-destructive" /><span className="text-destructive">{testResult.message || 'Failed'}</span></>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Permissions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Permissions</CardTitle>
          <CardDescription>Control what Billy is allowed to do</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Allow Order Placement</p>
              <p className="text-xs text-muted-foreground">
                Let Billy place and cancel real orders (always confirms first)
              </p>
            </div>
            <Switch
              checked={settings.allow_orders}
              onCheckedChange={(v) => setSettings((s) => ({ ...s, allow_orders: v }))}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Allow Strategy Creation</p>
              <p className="text-xs text-muted-foreground">
                Let Billy create Flow Editor strategies and Python strategies
              </p>
            </div>
            <Switch
              checked={settings.allow_strategies}
              onCheckedChange={(v) => setSettings((s) => ({ ...s, allow_strategies: v }))}
            />
          </div>
        </CardContent>
      </Card>

      <Button onClick={handleSave} disabled={isSaving} className="w-full bg-amber-500 hover:bg-amber-600">
        {isSaving ? (
          <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Saving...</>
        ) : (
          <><Save className="w-4 h-4 mr-2" />Save Settings</>
        )}
      </Button>
    </div>
  )
}
