/**
 * Open-gauge score dial — the `Lock Screen Widget / Circular / Open Gauge 2`
 * frame on the Recommendations screen (node 420:125).
 *
 * A 270° arc opening at the bottom, with the value as text in the centre and
 * the range labelled at each end. The number is always rendered as text, so the
 * reading never depends on colour.
 */
export default function ScoreGauge({
  value,
  min = 0,
  max = 100,
  label,
}: {
  value: number;
  min?: number;
  max?: number;
  /** Accessible name, e.g. "Match score for McMaster University". */
  label: string;
}) {
  const span = Math.max(max - min, 1);
  const fraction = Math.min(Math.max((value - min) / span, 0), 1);

  const R = 45;
  const CIRCUMFERENCE = 2 * Math.PI * R;
  const SWEEP_DEG = 270;
  const arcLength = CIRCUMFERENCE * (SWEEP_DEG / 360);

  // Arc starts bottom-left (135°) and runs clockwise.
  const endAngle = ((135 + SWEEP_DEG * fraction) * Math.PI) / 180;
  const dotX = 50 + R * Math.cos(endAngle);
  const dotY = 50 + R * Math.sin(endAngle);

  return (
    <div className="flex w-[180px] shrink-0 flex-col items-center md:w-[210px]">
      <div className="relative w-full">
        <svg
          viewBox="0 0 100 100"
          className="w-full"
          role="img"
          aria-label={`${label}: ${Math.round(value)} out of ${max}`}
        >
          <g transform="rotate(135 50 50)">
            {/* Track. A recessive neutral rather than the design's pale green,
                which disappears when the gauge sits on a pale green surface. */}
            <circle
              cx="50"
              cy="50"
              r={R}
              fill="none"
              stroke="rgb(0 0 0 / 0.12)"
              strokeWidth="9"
              strokeLinecap="round"
              strokeDasharray={`${arcLength} ${CIRCUMFERENCE}`}
            />
            {/* Value */}
            <circle
              cx="50"
              cy="50"
              r={R}
              fill="none"
              stroke="var(--color-unify-green)"
              strokeWidth="9"
              strokeLinecap="round"
              strokeDasharray={`${arcLength * fraction} ${CIRCUMFERENCE}`}
            />
          </g>
          {/* End-of-value indicator */}
          <circle cx={dotX} cy={dotY} r="5.5" fill="var(--color-unify-green)" />
          <circle cx={dotX} cy={dotY} r="2.4" fill="white" />
        </svg>

        {/* Centre value */}
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <span className="text-[clamp(2rem,3.4vw,3.25rem)] leading-none text-unify-green-dark">
            {Math.round(value)}
          </span>
        </div>
      </div>

      {/* Range labels sit in the gauge's open bottom */}
      <div className="-mt-5 flex w-[78%] items-center justify-between text-[clamp(0.875rem,1vw,1.125rem)] text-black">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}
