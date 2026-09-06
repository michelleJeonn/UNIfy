import { useNavigate } from "react-router-dom";
import type { ReactNode } from "react";

type PageHeaderProps = {
  title: string;
  description?: string;
  /** Where "Back to Roadmap" goes. */
  backTo?: string;
};

/**
 * Header for the checkpoint detail screens — Figma nodes 558:277 (Eligibility),
 * 585:1011 (Required Documents) and 585:1029 (Financial Aid), which share one
 * layout: a 62px title, then hairline-separated labelled sections.
 */
export default function PageHeader({
  title,
  description,
  backTo = "/roadmap",
}: PageHeaderProps) {
  const navigate = useNavigate();

  return (
    <div className="mb-10">
      <button
        onClick={() => navigate(backTo)}
        className="h-[44px] cursor-pointer rounded-pill bg-unify-green px-6 text-[18px] transition hover:brightness-95 active:translate-y-px"
      >
        Back to Roadmap
      </button>

      <h1 className="mt-8 text-[clamp(2.25rem,4vw,3.875rem)] leading-[1.11] tracking-[-0.02em]">
        {title}
      </h1>

      {description && (
        <p className="mt-3 max-w-[1065px] text-[clamp(1rem,1.15vw,1.1875rem)] leading-snug text-black/70">
          {description}
        </p>
      )}
    </div>
  );
}

/**
 * One hairline-separated block: a label, then its content.
 * Matches the "Anticipated Admission Range" / "Required Courses" rows.
 */
export function CheckpointSection({
  label,
  children,
}: {
  label: string;
  children?: ReactNode;
}) {
  return (
    <section className="border-t border-unify-rule py-8">
      <h2 className="text-[clamp(1rem,1.15vw,1.1875rem)] font-semibold">
        {label}
      </h2>
      {children && (
        <div className="mt-4 max-w-[817px] text-[clamp(1rem,1.15vw,1.1875rem)] leading-relaxed">
          {children}
        </div>
      )}
    </section>
  );
}

/** Placeholder for a section the API doesn't populate yet. */
export function NoData({ note }: { note: string }) {
  return <p className="text-black/50">{note}</p>;
}
