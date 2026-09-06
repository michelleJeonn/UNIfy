import { Link } from "react-router-dom";
import NavBar from "../components/NavBar";

/**
 * Admissions Services — Figma `Services` frame (node 558:179).
 *
 * The header component links here, so the route exists. The Figma frame's body
 * copy is still an unwritten placeholder ("At UnIfy, ..."), so rather than ship
 * that literal string this renders the design's headline plus a short summary
 * of what the product actually does today. Replace once the copy lands.
 */
export default function Services() {
  return (
    <div className="min-h-screen bg-white text-black">
      <NavBar />

      <main className="mx-auto max-w-[1728px] px-6 pb-24 pt-[120px] md:px-10 lg:px-[182px] lg:pt-[200px]">
        <h1 className="text-[clamp(3rem,6vw,6.75rem)] leading-[1.08] tracking-[-0.02em]">
          Admissions Services
        </h1>

        <div className="mt-8 max-w-[1144px] space-y-6 text-[clamp(1rem,1.3vw,1.6875rem)] leading-relaxed">
          <p>
            UNIfy matches your academic profile and accessibility needs against
            the published accommodation records of 28 Ontario universities, then
            builds a step-by-step admissions roadmap around the schools that fit
            best.
          </p>
        </div>

        <Link
          to="/information"
          className="mt-10 inline-flex h-[57px] items-center rounded-pill bg-unify-green px-7 text-[clamp(1.125rem,1.3vw,1.625rem)] transition hover:brightness-95"
        >
          Build my roadmap
        </Link>
      </main>
    </div>
  );
}
