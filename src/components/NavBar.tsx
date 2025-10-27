import { Link } from "react-router-dom";
import { useState } from "react";
import AccessibilityMenu from "./AccessibilityMenu";

export default function NavBar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <nav className="w-full px-6 py-4 shadow-md bg-white fixed top-0 left-0 z-50">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          {/* Logo */}
          <div className="flex items-center space-x-2">
            <img src="/logo.svg" alt="Logo" className="h-12 w-12" />
            <Link to="/" className="font-bold text-xl">
              UNIfy
            </Link>
          </div>

          <div className="flex items-center space-x-8">
            {/* Nav Links */}
            <ul className="hidden md:flex space-x-8 text-sm font-medium">
              <li>
                <Link to="/about" className="hover:text-gray-500">
                  About us
                </Link>
              </li>
              {/* Removing this because there's nothing to add here per Figma doc */}
              {/* <li>
                <Link to="/services" className="hover:text-gray-500">
                  Services
                </Link>
              </li> */}
            </ul>

            {/* Hamburger Menu */}
            <div className="cursor-pointer" onClick={() => setOpen(!open)}>
              <div className="space-y-1">
                <div className="w-7 h-0.5 bg-black"></div>
                <div className="w-7 h-0.5 bg-black"></div>
                <div className="w-7 h-0.5 bg-black"></div>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Accessibility Menu */}
      <AccessibilityMenu open={open} onClose={() => setOpen(false)} />
    </>
  );
}
