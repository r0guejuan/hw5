interface Props {
  tie: string;
  label: string;
  size?: number;
}

/** An original drawing of a bulldog mascot. Only the bow tie color changes. */
export function HandsomeDan({ tie, label, size = 100 }: Props) {
  const line = "#3b2a20";
  return (
    <svg className="dan" width={size} height={size} viewBox="0 0 120 120" role={label ? "img" : undefined} aria-label={label || undefined} aria-hidden={label ? undefined : true}>
      <path d="M28 36C12 18 2 36 12 56L34 46Z" fill="#7a5238" stroke={line} strokeWidth="2.5" strokeLinejoin="round" />
      <path d="M92 36C108 18 118 36 108 56L86 46Z" fill="#7a5238" stroke={line} strokeWidth="2.5" strokeLinejoin="round" />
      <ellipse cx="60" cy="56" rx="42" ry="37" fill="#f4e8d6" stroke={line} strokeWidth="2.5" />
      <path d="M26 42C30 26 48 24 54 34C56 44 52 58 40 60C32 60 26 52 26 42Z" fill="#c9986a" />
      <path d="M50 28Q60 34 70 28M52 35Q60 39 68 35" fill="none" stroke={line} strokeWidth="2" strokeLinecap="round" />
      <path d="M36 42Q44 37 51 43M69 43Q76 37 84 42" fill="none" stroke={line} strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="44" cy="50" r="5.5" fill={line} />
      <circle cx="76" cy="50" r="5.5" fill={line} />
      <circle cx="46" cy="48" r="1.8" fill="#fff" />
      <circle cx="78" cy="48" r="1.8" fill="#fff" />
      <ellipse cx="60" cy="87" rx="24" ry="9" fill="#e9d8bf" stroke={line} strokeWidth="2.5" />
      <ellipse cx="42" cy="71" rx="21" ry="14" fill="#fbf5ea" stroke={line} strokeWidth="2.5" />
      <ellipse cx="78" cy="71" rx="21" ry="14" fill="#fbf5ea" stroke={line} strokeWidth="2.5" />
      <path d="M44 87L48 74L53 87ZM67 87L72 74L76 87Z" fill="#fff" stroke={line} strokeWidth="2" strokeLinejoin="round" />
      <path d="M49 58Q60 53 71 58Q70 67 60 69Q50 67 49 58Z" fill="#2b1d16" />
      <ellipse cx="56" cy="59" rx="3" ry="1.5" fill="#6f5a4e" />
      <path d="M60 100L36 92Q32 104 36 118L60 110Z" fill={tie} stroke={line} strokeWidth="2.5" strokeLinejoin="round" />
      <path d="M60 100L84 92Q88 104 84 118L60 110Z" fill={tie} stroke={line} strokeWidth="2.5" strokeLinejoin="round" />
      <rect x="53" y="98" width="14" height="14" rx="4" fill={tie} stroke={line} strokeWidth="2.5" />
    </svg>
  );
}
