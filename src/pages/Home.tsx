import { Link } from "react-router-dom";
import NavBar from "../components/NavBar";

/**
 * Landing page — Figma `MacBook Pro 16" - 1` (node 3:2).
 *
 * Hero headline left, logo with its two rotated swoosh ellipses right, and a
 * full-width "Get Started" pill beneath the copy.
 */
export default function Home() {
  return (
    // overflow-x-clip: the swoosh ellipses are intentionally wider than the
    // logo column and would otherwise push the page sideways at tablet widths.
    <div className="min-h-screen overflow-x-clip bg-white text-black">
      <NavBar />

      {/* Padding-driven rather than min-h-screen + items-center: at short
          viewport heights, centring taller-than-screen content pushes the top
          of the headline above the scroll origin, where it can't be reached. */}
      {/* Horizontal padding and the logo column are percentages of the 1728px
          canvas (154/1728 ≈ 8.9%, 490/1728 ≈ 28%) so the headline keeps its
          measure — and its three-line wrap — as the viewport narrows. */}
      <main className="mx-auto flex max-w-[1728px] flex-col-reverse items-center gap-12 px-6 pb-24 pt-[120px] md:px-10 lg:flex-row lg:gap-[3.4%] lg:px-[8.9%] lg:pb-32 lg:pt-[190px]">
        {/* Copy */}
        <div className="w-full lg:max-w-[900px] lg:flex-1">
          <h1 className="text-[clamp(3rem,7vw,6.75rem)] leading-[1.08] tracking-[-0.02em]">
            A personalized path to your dream university.
          </h1>

          <p className="mt-8 max-w-[807px] text-[clamp(1.0625rem,1.6vw,1.6875rem)] leading-snug">
            Making university admissions accessible for all, one step at a time
          </p>

          <Link
            to="/login"
            className="mt-10 flex h-[64px] w-full max-w-[668px] items-center justify-center rounded-[22px] bg-unify-green text-[clamp(1.375rem,2.3vw,2.4375rem)] text-black shadow-[0_4px_12px_rgba(0,0,0,0.25)] transition hover:brightness-95 active:translate-y-px md:h-[77px]"
          >
            Get Started
          </Link>
        </div>

        {/* Logo + swooshes */}
        <div className="relative flex w-full shrink-0 items-center justify-center lg:w-[34%]">
          <img
            src="/logo.svg"
            alt="UNIfy — a graduation cap resting on an open book"
            className="relative z-10 w-full max-w-[490px] object-contain"
          />
          <img
            src="/icons/hero-swoosh.svg"
            alt=""
            aria-hidden="true"
            className="pointer-events-none absolute bottom-[8%] left-1/2 z-0 w-[115%] max-w-none -translate-x-1/2 rotate-[13.32deg] select-none"
          />
          <img
            src="/icons/hero-swoosh.svg"
            alt=""
            aria-hidden="true"
            className="pointer-events-none absolute bottom-[2%] left-[48%] z-0 w-[115%] max-w-none -translate-x-1/2 rotate-[13.32deg] select-none"
          />
        </div>
      </main>
    </div>
  );
}
