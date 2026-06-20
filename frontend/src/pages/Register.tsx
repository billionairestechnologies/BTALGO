import { ArrowLeft, Check, Eye, EyeOff, Loader2, Mail, RefreshCw, ShieldCheck } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { brand } from '@/config/branding'
import { cn } from '@/lib/utils'
import { showToast } from '@/utils/toast'

interface PasswordRequirements {
  length: boolean
  uppercase: boolean
  lowercase: boolean
  number: boolean
  special: boolean
}

function calculatePasswordStrength(password: string): number {
  let score = 0
  if (password.length >= 8) score += 20
  if (password.length >= 12) score += 10
  if (password.length >= 16) score += 10
  if (/[A-Z]/.test(password)) score += 15
  if (/[a-z]/.test(password)) score += 15
  if (/[0-9]/.test(password)) score += 15
  if (/[!@#$%^&*]/.test(password)) score += 15
  return score
}

function checkPasswordRequirements(password: string): PasswordRequirements {
  return {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[!@#$%^&*]/.test(password),
  }
}

function RequirementItem({ met, children }: { met: boolean; children: React.ReactNode }) {
  return (
    <div
      className={cn(
        'flex items-center gap-2 text-sm py-1 transition-colors',
        met ? 'text-green-500' : 'text-muted-foreground'
      )}
    >
      <Check className={cn('h-4 w-4', met ? 'opacity-100' : 'opacity-0')} />
      <span>{children}</span>
    </div>
  )
}

export default function Register() {
  const navigate = useNavigate()
  const [isCheckingSetup, setIsCheckingSetup] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [step, setStep] = useState<'details' | 'otp'>('details')
  const [error, setError] = useState<string | null>(null)
  const [otpCode, setOtpCode] = useState('')
  const [pendingEmail, setPendingEmail] = useState('')
  const [resendCooldown, setResendCooldown] = useState(30)
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  })

  const requirements = useMemo(
    () => checkPasswordRequirements(formData.password),
    [formData.password]
  )
  const passwordStrength = useMemo(
    () => calculatePasswordStrength(formData.password),
    [formData.password]
  )
  const passwordsMatch = formData.password === formData.confirmPassword
  const canSubmit =
    Object.values(requirements).every(Boolean) &&
    passwordsMatch &&
    Object.values(formData).every((value) => value.trim() !== '')

  useEffect(() => {
    const checkSetup = async () => {
      try {
        const response = await fetch('/auth/check-setup', { credentials: 'include' })
        const data = await response.json()
        if (data.needs_setup) {
          navigate('/setup', { replace: true })
          return
        }
      } catch (_err) {
      } finally {
        setIsCheckingSetup(false)
      }
    }
    checkSetup()
  }, [navigate])

  useEffect(() => {
    if (step !== 'otp' || resendCooldown <= 0) return
    const timer = window.setInterval(() => {
      setResendCooldown((current) => (current > 0 ? current - 1 : 0))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [step, resendCooldown])

  const strengthLabel = () => {
    if (passwordStrength >= 80) return { label: 'Strong', color: 'text-green-500' }
    if (passwordStrength >= 50) return { label: 'Medium', color: 'text-yellow-500' }
    if (passwordStrength > 0) return { label: 'Weak', color: 'text-red-500' }
    return { label: '', color: '' }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const fetchCsrfToken = async () => {
    const response = await fetch('/auth/csrf-token', { credentials: 'include' })
    const data = await response.json()
    return data.csrf_token as string
  }

  const handleStartRegistration = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return

    setIsLoading(true)
    setError(null)

    try {
      const csrfToken = await fetchCsrfToken()
      const response = await fetch('/auth/register/start', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
          username: formData.username,
          email: formData.email,
          password: formData.password,
          confirm_password: formData.confirmPassword,
        }),
      })
      const data = await response.json()

      if (!response.ok || data.status === 'error') {
        setError(data.message || 'Could not send verification code.')
        return
      }

      setPendingEmail(data.email || formData.email)
      setStep('otp')
      setResendCooldown(30)
      showToast.success('Verification code sent to your email', 'system')
    } catch (_err) {
      setError('Could not send verification code. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    try {
      const csrfToken = await fetchCsrfToken()
      const response = await fetch('/auth/register/verify', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
          email: pendingEmail,
          otp_code: otpCode,
        }),
      })
      const data = await response.json()

      if (!response.ok || data.status === 'error') {
        setError(data.message || 'Verification failed.')
        return
      }

      showToast.success('Account created successfully', 'system')
      navigate('/login', { replace: true })
    } catch (_err) {
      setError('Verification failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleResend = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const csrfToken = await fetchCsrfToken()
      const response = await fetch('/auth/register/resend', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ email: pendingEmail }),
      })
      const data = await response.json()

      if (!response.ok || data.status === 'error') {
        setError(data.message || 'Could not resend verification code.')
        return
      }

      setResendCooldown(30)
      showToast.success('A new verification code has been sent', 'system')
    } catch (_err) {
      setError('Could not resend verification code. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  if (isCheckingSetup) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const strength = strengthLabel()

  return (
    <div className="min-h-screen flex items-center justify-center py-8 px-4">
      <div className="container max-w-6xl">
        <div className="flex flex-col lg:flex-row items-center justify-between gap-8 lg:gap-16">
          <Card className="w-full max-w-md shadow-xl order-1 lg:order-2">
            <CardHeader className="text-center">
              <div className="flex justify-center mb-4">
                <img src="/logo.png" alt={brand.productName} className="h-20 w-20" />
              </div>
              <CardTitle className="text-2xl">Create Your Account</CardTitle>
              <CardDescription>
                {step === 'details'
                  ? `Join ${brand.productName} and set up your trading workspace`
                  : 'Enter the email verification code to finish registration'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {step === 'details' ? (
                <form onSubmit={handleStartRegistration} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="username">Username</Label>
                    <Input
                      id="username"
                      name="username"
                      value={formData.username}
                      onChange={handleInputChange}
                      placeholder="Choose a username"
                      autoComplete="username"
                      disabled={isLoading}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      name="email"
                      type="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      placeholder="name@company.com"
                      autoComplete="email"
                      disabled={isLoading}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <div className="relative">
                      <Input
                        id="password"
                        name="password"
                        type={showPassword ? 'text' : 'password'}
                        value={formData.password}
                        onChange={handleInputChange}
                        placeholder="Create a password"
                        autoComplete="new-password"
                        className="pr-10"
                        disabled={isLoading}
                        required
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                        onClick={() => setShowPassword((current) => !current)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                      >
                        {showPassword ? (
                          <EyeOff className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <Eye className="h-4 w-4 text-muted-foreground" />
                        )}
                      </Button>
                    </div>
                    <Progress value={passwordStrength} className="h-2" />
                    {strength.label && (
                      <p className={cn('text-xs font-medium', strength.color)}>{strength.label}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm Password</Label>
                    <div className="relative">
                      <Input
                        id="confirmPassword"
                        name="confirmPassword"
                        type={showConfirmPassword ? 'text' : 'password'}
                        value={formData.confirmPassword}
                        onChange={handleInputChange}
                        placeholder="Confirm your password"
                        autoComplete="new-password"
                        className="pr-10"
                        disabled={isLoading}
                        required
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                        onClick={() => setShowConfirmPassword((current) => !current)}
                        aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                      >
                        {showConfirmPassword ? (
                          <EyeOff className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <Eye className="h-4 w-4 text-muted-foreground" />
                        )}
                      </Button>
                    </div>
                    {formData.confirmPassword && (
                      <p className={cn('text-xs', passwordsMatch ? 'text-green-500' : 'text-red-500')}>
                        {passwordsMatch ? 'Passwords match' : 'Passwords do not match'}
                      </p>
                    )}
                  </div>

                  <div className="bg-muted rounded-lg p-4 space-y-1">
                    <RequirementItem met={requirements.length}>Minimum 8 characters</RequirementItem>
                    <RequirementItem met={requirements.uppercase}>
                      At least 1 uppercase letter (A-Z)
                    </RequirementItem>
                    <RequirementItem met={requirements.lowercase}>
                      At least 1 lowercase letter (a-z)
                    </RequirementItem>
                    <RequirementItem met={requirements.number}>
                      At least 1 number (0-9)
                    </RequirementItem>
                    <RequirementItem met={requirements.special}>
                      At least 1 special character (!@#$%^&*)
                    </RequirementItem>
                  </div>

                  {error && (
                    <Alert variant="destructive">
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  <Button type="submit" className="w-full" disabled={!canSubmit || isLoading}>
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Sending code...
                      </>
                    ) : (
                      <>
                        <Mail className="mr-2 h-4 w-4" />
                        Send verification code
                      </>
                    )}
                  </Button>
                </form>
              ) : (
                <form onSubmit={handleVerifyOtp} className="space-y-4">
                  <Alert>
                    <ShieldCheck className="h-4 w-4" />
                    <AlertTitle>Check your inbox</AlertTitle>
                    <AlertDescription>
                      We sent a 6-digit verification code to <strong>{pendingEmail}</strong>.
                    </AlertDescription>
                  </Alert>

                  <div className="space-y-2">
                    <Label htmlFor="otp_code">Verification code</Label>
                    <Input
                      id="otp_code"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      pattern="[0-9]{6}"
                      maxLength={6}
                      placeholder="123456"
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      disabled={isLoading}
                      autoFocus
                      required
                      className="font-mono text-center text-lg tracking-widest"
                    />
                  </div>

                  {error && (
                    <Alert variant="destructive">
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setStep('details')
                        setOtpCode('')
                        setError(null)
                      }}
                      disabled={isLoading}
                    >
                      <ArrowLeft className="mr-1 h-4 w-4" />
                      Back
                    </Button>
                    <Button type="submit" className="flex-1" disabled={isLoading || otpCode.length !== 6}>
                      {isLoading ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Verifying...
                        </>
                      ) : (
                        'Verify and create account'
                      )}
                    </Button>
                  </div>

                  <Button
                    type="button"
                    variant="ghost"
                    className="w-full"
                    onClick={handleResend}
                    disabled={isLoading || resendCooldown > 0}
                  >
                    <RefreshCw className="mr-2 h-4 w-4" />
                    {resendCooldown > 0
                      ? `Resend code in ${resendCooldown}s`
                      : 'Resend verification code'}
                  </Button>
                </form>
              )}
            </CardContent>
          </Card>

          <div className="flex-1 max-w-xl text-center lg:text-left order-2 lg:order-1">
            <h1 className="text-4xl lg:text-5xl font-bold mb-6">
              Build on <span className="text-primary">{brand.productName}</span>
            </h1>
            <p className="text-lg lg:text-xl mb-8 text-muted-foreground">
              Create your workspace, connect your broker apps, and manage strategies from one place.
            </p>

            <Alert className="mb-6">
              <Mail className="h-4 w-4" />
              <AlertTitle>Email verification enabled</AlertTitle>
              <AlertDescription>
                Registration uses one-time email codes so every workspace starts with a verified owner.
              </AlertDescription>
            </Alert>

            <div className="flex justify-center lg:justify-start">
              <Button variant="outline" asChild>
                <Link to="/login">Already have an account? Sign in</Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
