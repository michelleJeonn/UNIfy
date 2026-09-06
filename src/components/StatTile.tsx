/**
 * KPI tile from the university cards on the Recommendations screen
 * (the `XR/XR Dialog` frames, nodes 423:5746 / 423:5775 / 423:5789).
 *
 * Icon, label, then the value. Identity is carried by the icon and the written
 * label, never by the tile colour alone.
 */

export type StatTone = "pale" | "green" | "blue";

const TONES: Record<
  StatTone,
  { surface: string; ink: string; icon: string }
> = {
  pale: {
    surface: "bg-unify-green-pale",
    ink: "text-unify-green-dark",
    icon: "/icons/stat-gpa.svg",
  },
  green: {
    surface: "bg-unify-green/40",
    ink: "text-unify-green-dark",
    icon: "/icons/stat-prereqs.svg",
  },
  blue: {
    surface: "bg-unify-blue-tint",
    ink: "text-unify-blue-deep",
    icon: "/icons/stat-accommodations.svg",
  },
};

export default function StatTile({
  tone,
  label,
  value,
  title,
}: {
  tone: StatTone;
  label: string;
  /** Rendered as-is; pass "—" when the value has no data behind it. */
  value: string;
  /** Optional tooltip explaining what the number counts. */
  title?: string;
}) {
  const t = TONES[tone];
  const unavailable = value === "—";

  return (
    <div
      title={title}
      className={`flex min-w-[120px] flex-1 flex-col items-center justify-between rounded-[12px] px-3 py-5 ${t.surface}`}
    >
      <img
        src={t.icon}
        alt=""
        aria-hidden="true"
        className="size-[38px] shrink-0 object-contain md:size-[46px]"
      />

      <p
        className={`mt-3 text-center text-[clamp(0.875rem,1.05vw,1.1875rem)] leading-tight ${t.ink}`}
      >
        {label}
      </p>

      <p
        className={`mt-2 text-[clamp(1.75rem,3vw,3rem)] leading-none ${t.ink} ${
          unavailable ? "opacity-45" : ""
        }`}
      >
        {value}
      </p>

      {unavailable && <span className="sr-only">No data available</span>}
    </div>
  );
}
