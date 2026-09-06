import type { ReactNode } from "react";

/**
 * Form primitives for the "Enter your information" wizard.
 * Figma nodes 313:2 / 335:26 / 342:96 and the `Dropdown` symbols (426:75).
 */

/** 43px dark-green field label. */
export function FieldLabel({
  htmlFor,
  children,
  className = "",
}: {
  htmlFor?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className={`block text-[clamp(1.5rem,2.6vw,2.6875rem)] leading-tight tracking-[-0.02em] text-unify-green-dark ${className}`}
    >
      {children}
    </label>
  );
}

/** Bordered select with the design's chevron. */
export function Select({
  id,
  name,
  value,
  onChange,
  options,
  placeholder,
  required,
  centered = false,
}: {
  id: string;
  name: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  options: readonly string[];
  placeholder: string;
  required?: boolean;
  centered?: boolean;
}) {
  return (
    <select
      id={id}
      name={name}
      value={value}
      onChange={onChange}
      required={required}
      className={`h-[56px] w-full cursor-pointer appearance-none rounded-field border border-black bg-white bg-[url('/icons/chevron-down.svg')] bg-[length:26px_15px] bg-[right_27px_center] bg-no-repeat pl-6 pr-[70px] text-[clamp(1rem,1.4vw,1.625rem)] tracking-[-0.02em] outline-none transition focus:ring-2 focus:ring-unify-green-dark ${
        centered ? "text-center" : "text-left"
      } ${value === "" ? "text-black/60" : "text-black"}`}
    >
      <option value="">{placeholder}</option>
      {options.map((o) => (
        <option key={o} value={o} className="text-black">
          {o}
        </option>
      ))}
    </select>
  );
}

/** Bordered multi-line box (Rectangle 18 — 1048×240, radius 15). */
export function TextArea({
  id,
  name,
  value,
  onChange,
  rows = 6,
  placeholder,
}: {
  id: string;
  name: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  rows?: number;
  placeholder?: string;
}) {
  return (
    <textarea
      id={id}
      name={name}
      value={value}
      onChange={onChange}
      rows={rows}
      placeholder={placeholder}
      className="w-full resize-y rounded-field border border-black bg-white px-6 py-4 text-[clamp(1rem,1.2vw,1.375rem)] outline-none transition focus:ring-2 focus:ring-unify-green-dark"
    />
  );
}

/** 50px ring radio used for Application Round and Type of Disability. */
export function RingRadio({
  name,
  value,
  label,
  checked,
  onChange,
}: {
  name: string;
  value: string;
  label: ReactNode;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-4">
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
        className="flex size-[50px] shrink-0 items-center justify-center rounded-full border-2 border-black transition peer-focus-visible:outline peer-focus-visible:outline-[3px] peer-focus-visible:outline-offset-2 peer-focus-visible:outline-unify-green-dark"
      >
        <span
          className={`size-[28px] rounded-full bg-unify-green transition-transform ${
            checked ? "scale-100" : "scale-0"
          }`}
        />
      </span>
      <span className="text-[clamp(1.125rem,1.6vw,1.75rem)] leading-tight">
        {label}
      </span>
    </label>
  );
}

/** The design's "+ Add more" affordance. */
export function AddMore({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mt-2 cursor-pointer text-[clamp(1rem,1.2vw,1.625rem)] tracking-[-0.02em] text-black underline-offset-4 transition hover:text-unify-green-dark hover:underline"
    >
      + Add more
    </button>
  );
}

/** Green pill button (131×57, radius 18). */
export function PillButton({
  children,
  onClick,
  type = "button",
  disabled,
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  disabled?: boolean;
  className?: string;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`h-[57px] min-w-[131px] cursor-pointer rounded-pill bg-unify-green px-7 text-[clamp(1.125rem,1.3vw,1.625rem)] tracking-[-0.02em] text-black transition hover:brightness-95 active:translate-y-px disabled:cursor-not-allowed disabled:bg-neutral-300 disabled:text-neutral-600 ${className}`}
    >
      {children}
    </button>
  );
}
