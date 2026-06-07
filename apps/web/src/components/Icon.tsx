// Material Symbols Outlined icon (loaded via the font link in index.html).
export function Icon({
  name,
  filled = false,
  className = "",
}: {
  name: string;
  filled?: boolean;
  className?: string;
}) {
  return (
    <span className={`material-symbols-outlined${filled ? " filled" : ""} ${className}`} aria-hidden>
      {name}
    </span>
  );
}
