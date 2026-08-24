import type { ReactNode, SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function IconBase({ children, ...props }: IconProps & { children: ReactNode }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{children}</svg>;
}

export function HomeIcon(props: IconProps) { return <IconBase {...props}><path d="m3 10 9-7 9 7" /><path d="M5 9v11h14V9" /><path d="M9 20v-6h6v6" /></IconBase>; }
export function WrenchIcon(props: IconProps) { return <IconBase {...props}><path d="M14.8 6.2a4 4 0 0 0-5-5l2.3 2.3-2.6 2.6-2.3-2.3a4 4 0 0 0 5 5l7.2 7.2a2.2 2.2 0 0 1-3.1 3.1l-7.2-7.2" /></IconBase>; }
export function BookIcon(props: IconProps) { return <IconBase {...props}><path d="M4 5.5A3.5 3.5 0 0 1 7.5 2H11v17H7.5A3.5 3.5 0 0 0 4 22Z" /><path d="M20 5.5A3.5 3.5 0 0 0 16.5 2H13v17h3.5A3.5 3.5 0 0 1 20 22Z" /></IconBase>; }
export function RouteIcon(props: IconProps) { return <IconBase {...props}><circle cx="6" cy="19" r="2" /><circle cx="18" cy="5" r="2" /><path d="M8 19h3a3 3 0 0 0 3-3V8a3 3 0 0 1 3-3" /></IconBase>; }
export function CarIcon(props: IconProps) { return <IconBase {...props}><path d="m5 11 1.5-4.5A2 2 0 0 1 8.4 5h7.2a2 2 0 0 1 1.9 1.5L19 11" /><path d="M3 12h18v6H3z" /><path d="M5 18v2M19 18v2" /><circle cx="7" cy="15" r="1" /><circle cx="17" cy="15" r="1" /></IconBase>; }
export function PlusIcon(props: IconProps) { return <IconBase {...props}><path d="M12 5v14M5 12h14" /></IconBase>; }
export function SendIcon(props: IconProps) { return <IconBase {...props}><path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" /></IconBase>; }
export function ChevronIcon(props: IconProps) { return <IconBase {...props}><path d="m8 10 4 4 4-4" /></IconBase>; }
export function FuelIcon(props: IconProps) { return <IconBase {...props}><path d="M4 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18" /><path d="M3 22h14M7 6h6v5H7zM16 7h2l2 3v7a2 2 0 0 1-4 0v-3" /></IconBase>; }
export function BoltIcon(props: IconProps) { return <IconBase {...props}><path d="m13 2-8 12h7l-1 8 8-12h-7Z" /></IconBase>; }
