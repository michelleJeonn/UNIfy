import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import NavBar from "../components/NavBar";

/**
 * Sign Up.
 *
 * The Figma file has no Sign Up frame, so this reuses the `Login` frame's
 * layout and tokens (node 15:15) with the existing four-field form.
 */
export default function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [error, setError] = useState("");

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setError("");
    navigate("/information");
  };

  return (
    <div className="min-h-screen bg-white text-black">
      <NavBar />

      <main className="mx-auto flex max-w-[1728px] flex-col items-center gap-12 px-6 pb-24 pt-[130px] md:px-10 lg:flex-row lg:gap-16 lg:px-[182px] lg:pb-32 lg:pt-[200px]">
        <div className="w-full lg:flex-1">
          <h1 className="text-[clamp(3.5rem,7vw,6.75rem)] leading-[1.08] tracking-[-0.02em]">
            Sign Up.
          </h1>
          <p className="mt-6 max-w-[589px] text-[clamp(1.0625rem,1.6vw,1.6875rem)] leading-snug">
            Create your UNIfy account to save your progress and build a
            personalized admissions roadmap.
          </p>
        </div>

        <div className="w-full rounded-card bg-white p-8 shadow-card md:p-[60px] lg:w-[709px] lg:shrink-0">
          <form className="space-y-6" onSubmit={handleSubmit} noValidate>
            <Field
              id="name"
              label="Name"
              type="text"
              value={form.name}
              onChange={handleChange}
              autoComplete="name"
            />
            <Field
              id="email"
              label="Email"
              type="email"
              value={form.email}
              onChange={handleChange}
              autoComplete="email"
            />
            <Field
              id="password"
              label="Password"
              type="password"
              value={form.password}
              onChange={handleChange}
              autoComplete="new-password"
            />
            <Field
              id="confirmPassword"
              label="Confirm Password"
              type="password"
              value={form.confirmPassword}
              onChange={handleChange}
              autoComplete="new-password"
            />

            {error && (
              <p role="alert" className="text-[18px] text-red-600">
                {error}
              </p>
            )}

            <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
              <p className="text-[19px]">
                Already have an account?{" "}
                <Link
                  to="/login"
                  className="text-unify-green-dark underline-offset-2 hover:underline"
                >
                  Log In.
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

function Field({
  id,
  label,
  type,
  value,
  onChange,
  autoComplete,
}: {
  id: string;
  label: string;
  type: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  autoComplete?: string;
}) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-[clamp(1.25rem,1.8vw,1.75rem)] text-unify-green-dark"
      >
        {label}
      </label>
      <input
        id={id}
        name={id}
        type={type}
        required
        value={value}
        onChange={onChange}
        autoComplete={autoComplete}
        className="mt-2 block h-[42px] w-full bg-unify-field px-3 text-[18px] outline-none focus:ring-2 focus:ring-unify-green-dark"
      />
    </div>
  );
}
