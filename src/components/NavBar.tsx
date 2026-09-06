import { Link, NavLink } from "react-router-dom";
import { useState } from "react";
import AccessibilityMenu from "./AccessibilityMenu";

/**
 * Site header — Figma `header` component (node 558:193).
 *
 * The design is a 1728px-wide bar: logo + wordmark hard left, "About us" and
 * "Services" toward the right, hamburger at the far right. Heights and type
 * sizes are scaled down from the canvas so the bar is usable at real viewport
 * widths while keeping the same proportions.
 */
export default function NavBar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <nav className="fixed top-0 left-0 z-50 w-full bg-white/95 shadow-header backdrop-blur-sm">
        <div className="mx-auto flex h-[84px] max-w-[1728px] items-center px-6 md:h-[96px] md:px-10 lg:px-[82px]">
          {/* Logo + wordmark */}
          <Link to="/" className="flex shrink-0 items-center gap-3 md:gap-4">
            <img
              src="/logo.svg"
              alt=""
              aria-hidden="true"
              className="h-[52px] w-[52px] shrink-0 object-contain md:h-[66px] md:w-[66px]"
            />
            <span className="text-[28px] font-bold leading-none tracking-tight md:text-[38px]">
              UNIfy
            </span>
          </Link>

          {/* Nav links */}
          <ul className="ml-auto hidden items-center gap-10 text-[18px] md:flex lg:gap-[110px] lg:text-[22px]">
            <li>
              <NavLink
                to="/about"
                className={({ isActive }) =>
                  `transition hover:text-unify-green-dark ${
                    isActive ? "text-unify-green-dark" : ""
                  }`
                }
              >
                About us
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/services"
                className={({ isActive }) =>
                  `transition hover:text-unify-green-dark ${
                    isActive ? "text-unify-green-dark" : ""
                  }`
                }
              >
                Services
              </NavLink>
            </li>
          </ul>

          {/* Accessibility menu trigger */}
          <button
            type="button"
            onClick={() => setOpen(true)}
            aria-label="Open accessibility settings"
            aria-expanded={open}
            aria-controls="accessibility-panel"
            className="ml-auto shrink-0 cursor-pointer rounded p-2 transition hover:opacity-60 md:ml-10 lg:ml-[92px]"
          >
            <img
              src="/icons/menu.svg"
              alt=""
              aria-hidden="true"
              className="h-[24px] w-[60px] md:h-[30px] md:w-[75px]"
            />
          </button>
        </div>
      </nav>

      <AccessibilityMenu open={open} onClose={() => setOpen(false)} />
    </>
  );
}
