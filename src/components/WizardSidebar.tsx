/**
 * "Enter your information" sidebar — the `fixed sidebar` group in Figma nodes
 * 313:2 / 335:26 / 342:96.
 *
 * A pale-green rounded panel: heading, supporting copy, then a three-step rail
 * where the current step is full opacity and the others sit at 40%.
 */

import { WIZARD_STEPS } from "../data/options";

export default function WizardSidebar({
  currentStep,
  onStepChange,
}: {
  /** 0-based index into WIZARD_STEPS. */
  currentStep: number;
  /** Jump back to an already-completed step. */
  onStepChange?: (step: number) => void;
}) {
  return (
    <aside className="w-full shrink-0 rounded-card bg-unify-green/30 p-8 shadow-panel md:p-[27px] lg:w-[508px]">
      <h1 className="text-[clamp(2.25rem,4.2vw,4.375rem)] leading-[1.13] tracking-[-0.02em]">
        Enter your information.
      </h1>

      <p className="mt-6 max-w-[487px] text-[clamp(1rem,1.2vw,1.625rem)] leading-snug tracking-[-0.02em]">
        Tell us a bit about your academic background and accessibility needs so
        we can build your custom university admissions roadmap.
      </p>

      <ol className="mt-10 lg:mt-[80px]">
        {WIZARD_STEPS.map((label, i) => {
          const isCurrent = i === currentStep;
          const isDone = i < currentStep;
          const canJump = isDone && Boolean(onStepChange);

          return (
            <li key={label} className="relative flex items-center gap-6 pb-[81px] last:pb-0">
              {/* Connector to the next step */}
              {i < WIZARD_STEPS.length - 1 && (
                <span
                  aria-hidden="true"
                  className={`absolute left-[25px] top-[50px] h-[81px] w-0 border-l-2 ${
                    isDone ? "border-black" : "border-black/40"
                  }`}
                />
              )}

              <span
                aria-hidden="true"
                className={`flex size-[50px] shrink-0 items-center justify-center rounded-full border-2 transition ${
                  isCurrent || isDone
                    ? "border-black"
                    : "border-black/40"
                }`}
              >
                <span
                  className={`size-[26px] rounded-full transition-transform ${
                    isDone ? "scale-100 bg-black" : isCurrent ? "scale-100 bg-unify-green" : "scale-0"
                  }`}
                />
              </span>

              {canJump ? (
                <button
                  type="button"
                  onClick={() => onStepChange?.(i)}
                  className="cursor-pointer text-left text-[clamp(1.0625rem,1.2vw,1.625rem)] tracking-[-0.02em] underline-offset-4 transition hover:underline"
                >
                  {label}
                </button>
              ) : (
                <span
                  aria-current={isCurrent ? "step" : undefined}
                  className={`text-[clamp(1.0625rem,1.2vw,1.625rem)] tracking-[-0.02em] ${
                    isCurrent ? "opacity-100" : "opacity-40"
                  }`}
                >
                  {label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
