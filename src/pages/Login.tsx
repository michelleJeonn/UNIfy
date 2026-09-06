import { useNavigate, Link } from "react-router-dom";
import NavBar from "../components/NavBar";
import type { FormEvent } from "react";

/**
 * Login — Figma `Login` frame (node 15:15).
 *
 * Oversized "Login." headline and supporting copy on the left, a floating
 * white card holding the form on the right.
 */
export default function Login() {
  const navigate = useNavigate();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    // Can add validation later
    navigate("/information");
  };

  return (
    <div className="min-h-screen bg-white text-black">
      <NavBar />

      <main className="mx-auto flex max-w-[1728px] flex-col items-center gap-12 px-6 pb-24 pt-[130px] md:px-10 lg:flex-row lg:gap-16 lg:px-[182px] lg:pb-32 lg:pt-[200px]">
        {/* Headline */}
        <div className="w-full lg:flex-1">
          <h1 className="text-[clamp(3.5rem,7vw,6.75rem)] leading-[1.08] tracking-[-0.02em]">
            Login.
          </h1>
          <p className="mt-6 max-w-[589px] text-[clamp(1.0625rem,1.6vw,1.6875rem)] leading-snug">
            Log in to save your progress and get a personalized admissions
            roadmap tailored to your needs.
          </p>
        </div>

        {/* Card */}
        <div className="w-full rounded-card bg-white p-8 shadow-card md:p-[75px] lg:w-[709px] lg:shrink-0">
          <form className="space-y-8" onSubmit={handleSubmit}>
            <div>
              <label
                htmlFor="email"
                className="block text-[clamp(1.5rem,2.2vw,2.375rem)] text-unify-green-dark"
              >
                Email
              </label>
              <input
                type="email"
                id="email"
                name="email"
                required
                autoComplete="email"
                className="mt-3 block h-[42px] w-full bg-unify-field px-3 text-[18px] outline-none focus:ring-2 focus:ring-unify-green-dark"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-[clamp(1.5rem,2.2vw,2.375rem)] text-unify-green-dark"
              >
                Password
              </label>
              <input
                type="password"
                id="password"
                name="password"
                required
                autoComplete="current-password"
                className="mt-3 block h-[42px] w-full bg-unify-field px-3 text-[18px] outline-none focus:ring-2 focus:ring-unify-green-dark"
              />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
              <p className="text-[19px]">
                Don’t have an account yet?{" "}
                <Link
                  to="/signup"
                  className="text-unify-green-dark underline-offset-2 hover:underline"
                >
                  Sign Up.
                </Link>
              </p>

              <button
                type="submit"
                className="h-[44px] w-[137px] cursor-pointer rounded-pill bg-unify-green text-[26px] tracking-[-0.02em] text-black transition hover:brightness-95 active:translate-y-px"
              >
                Go!
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
