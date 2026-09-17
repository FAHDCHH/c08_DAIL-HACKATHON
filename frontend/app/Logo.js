export default function Logo({ size = 34 }) {
  // Three stylised figures echoing the client's mark (original demo asset, not their file).
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden="true">
      {[4, 18, 32].map((x, i) => (
        <g key={i} fill="#228608">
          <circle cx={x + 6} cy="12" r="4.2" />
          <path d={`M${x + 6} 17 L${x + 1} 33 M${x + 6} 17 L${x + 11} 33 M${x + 6} 22 L${x + 6} 40`}
                stroke="#228608" strokeWidth="3.4" strokeLinecap="round" />
        </g>
      ))}
    </svg>
  );
}
