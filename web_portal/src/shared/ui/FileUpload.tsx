import { useRef, useState } from 'react'

interface FileUploadProps {
  accept?: string
  maxSizeMB?: number
  onFileSelect: (file: File) => void
  label?: string
  className?: string
}

export function FileUpload({ accept = 'image/*,.pdf', maxSizeMB = 10, onFileSelect, label = 'Загрузить файл', className = '' }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [error, setError] = useState<string | null>(null)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.size > maxSizeMB * 1024 * 1024) {
      setError(`Файл слишком большой (макс. ${maxSizeMB} МБ)`)
      return
    }

    setError(null)
    onFileSelect(file)
  }

  return (
    <div className={className}>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={handleChange}
      />
      <button
        type="button"
        className="inline-flex items-center gap-2 px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-sm text-text-secondary hover:border-accent hover:text-accent transition-all duration-fast cursor-pointer"
        onClick={() => inputRef.current?.click()}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
        {label}
      </button>
      {error && <p className="text-xs text-danger mt-1">{error}</p>}
    </div>
  )
}
