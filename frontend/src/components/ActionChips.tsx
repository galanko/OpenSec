interface ActionChip {
  label: string
  prompt: string
}

const ACTIONS: ActionChip[] = [
  { label: 'Enrich finding', prompt: 'Enrich this finding with CVE details, severity analysis, and exploit information' },
  { label: 'Find owner', prompt: 'Find the owner of this asset by analyzing CMDB records and prior ticket history' },
  { label: 'Check exposure', prompt: 'Check the exposure and reachability of this asset - is it internet-facing? What is the blast radius?' },
  { label: 'Build remediation plan', prompt: 'Build a remediation plan with step-by-step fix instructions, mitigations, and a definition of done' },
  { label: 'Validate closure', prompt: 'Validate whether this finding has been fixed and recommend close or reopen' },
]

interface ActionChipsProps {
  onAction: (prompt: string) => void
  disabled?: boolean
}

export default function ActionChips({ onAction, disabled }: ActionChipsProps) {
  return (
    <div className="flex flex-wrap gap-2 max-w-3xl">
      {ACTIONS.map((action) => (
        <button
          key={action.label}
          onClick={() => onAction(action.prompt)}
          disabled={disabled}
          className="px-4 py-2 rounded-full border border-primary/10 bg-white text-xs font-medium text-primary hover:bg-primary-container/30 shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {action.label}
        </button>
      ))}
    </div>
  )
}
