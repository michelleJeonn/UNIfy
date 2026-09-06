import { useEffect, useRef, useState } from "react";

type AccessibilityMenuProps = {
  open: boolean;
  onClose: () => void;
};

/**
 * Accessibility drawer — Figma `Accessibility` frame (node 24:31).
 *
 * A 407px panel: centred SemiBold title, then hairline-separated rows for
 * Text Size (two ring-style radios) and three pill toggles.
 *
 * NOTE: as before this redesign, the controls hold their own visual state but
 * do not yet change the page. Wiring them to real preferences is a behaviour
 * change and was deliberately left out of this visual rebuild.
 */
export default function AccessibilityMenu({
  open,
  onClose,
}: AccessibilityMenuProps) {
  const [textSize, setTextSize] = useState<"normal" | "large">("normal");
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on Escape, matching the drawer's dismissable intent.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <>
      {/* Scrim */}
      <div
        onClick={onClose}
        aria-hidden="true"
        className={`fixed inset-0 z-40 bg-black/20 transition-opacity duration-300 ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />

      <div
        id="accessibility-panel"
        ref={panelRef}
        role="dialog"
        aria-label="Accessibility Settings"
        aria-hidden={!open}
        className={`fixed right-0 top-0 z-50 h-full w-full max-w-[407px] overflow-y-auto bg-white shadow-panel transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Close accessibility settings"
          className="absolute right-5 top-5 cursor-pointer rounded p-1 text-2xl leading-none text-black/60 transition hover:text-black"
        >
          ✕
        </button>

        <div className="px-[26px] pb-16 pt-[60px]">
          <h2 className="text-center text-[28px] font-semibold leading-tight">
            Accessibility Settings
          </h2>

          <Rule className="mt-6" />

          {/* Text Size */}
          <fieldset className="pt-6">
            <legend className="text-[22px]">Text Size</legend>
            <div className="mt-4 flex items-center gap-x-8">
              <RingRadio
                name="textSize"
                value="normal"
                label="Normal"
                labelClassName="text-[16px]"
                checked={textSize === "normal"}
                onChange={() => setTextSize("normal")}
              />
              <RingRadio
                name="textSize"
                value="large"
                label="Large"
                labelClassName="text-[23px]"
                checked={textSize === "large"}
                onChange={() => setTextSize("large")}
              />
            </div>
          </fieldset>

          <Rule className="mt-7" />

          <Toggle label="Dark Mode" labelClassName="text-[20px]" />
          <Rule />
          <Toggle label="Dyslexia-Friendly Font" />
          <Rule />
          <Toggle label="Keyboard Accessibility" />
          <Rule />
        </div>
      </div>
    </>
  );
}

function Rule({ className = "" }: { className?: string }) {
  return (
    <hr className={`border-0 border-t border-unify-rule ${className}`} />
  );
}

/** The design's radio: a 43px hollow ring that fills when selected. */
function RingRadio({
  name,
  value,
  label,
  checked,
  onChange,
  labelClassName = "",
}: {
  name: string;
  value: string;
  label: string;
  checked: boolean;
  onChange: () => void;
  labelClassName?: string;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-3">
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        onChange={onChange}
        className="peer sr-only"
      />
      <span
        aria-hidden="true"
        className="flex size-[43px] shrink-0 items-center justify-center rounded-full border border-black transition peer-focus-visible:outline peer-focus-visible:outline-[3px] peer-focus-visible:outline-offset-2 peer-focus-visible:outline-unify-green-dark"
      >
        <span
          className={`size-[25px] rounded-full bg-unify-green transition-transform ${
            checked ? "scale-100" : "scale-0"
          }`}
        />
      </span>
      <span className={labelClassName}>{label}</span>
    </label>
  );
}

/** The design's 96×38 pill toggle with a 30px knob. */
function Toggle({
  label,
  labelClassName = "text-[19px]",
}: {
  label: string;
  labelClassName?: string;
}) {
  const [on, setOn] = useState(false);
  return (
    <div className="flex items-center justify-between gap-4 py-6">
      <span className={labelClassName}>{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={on}
        aria-label={label}
        onClick={() => setOn(!on)}
        className={`relative h-[38px] w-[96px] shrink-0 cursor-pointer rounded-[90px] transition-colors ${
          on ? "bg-unify-green" : "bg-unify-field"
        }`}
      >
        <span
          aria-hidden="true"
          className={`absolute top-1/2 size-[30px] -translate-y-1/2 rounded-full bg-white shadow-sm transition-all ${
            on ? "left-[62px]" : "left-[4px]"
          }`}
        />
      </button>
    </div>
  );
}
