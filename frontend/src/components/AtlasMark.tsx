export function AtlasMark({ small = false }: { small?: boolean }) {
  return (
    <svg className={small ? 'atlas-mark atlas-mark--small' : 'atlas-mark'} viewBox="0 0 56 56" aria-hidden="true">
      <circle cx="28" cy="28" r="23" fill="none" stroke="currentColor" strokeWidth=".8" opacity=".4" />
      <circle cx="28" cy="28" r="15" fill="none" stroke="currentColor" strokeWidth=".8" opacity=".65" />
      <path d="M7 31c9-8 15-15 22-8s12 13 20 4M12 18c8 2 13 8 16 16s8 10 16 8" fill="none" stroke="currentColor" strokeWidth="1.15" />
      <circle cx="28" cy="28" r="2.5" fill="currentColor" />
      <path d="M28 1v6M28 49v6M1 28h6M49 28h6" stroke="currentColor" strokeWidth=".8" opacity=".55" />
    </svg>
  )
}
