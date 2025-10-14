import { useNavigate } from "react-router-dom";
import NavBar from "../components/NavBar";
import { useState, type FormEvent } from "react";
import { signInUser } from "../services/auth";

export default function Login() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    const formData = new FormData(e.currentTarget);
    const email = formData.get('email')?.toString() || '';
    const password = formData.get('password')?.toString() || '';

    console.log('Attempting login with:', { email });

    const result = await signInUser({ email, password });

    if (result.success) {
      console.log('Login successful!');
      navigate("/information");
    } else {
      console.error('Login failed:', result.error);
      setError(result.error || 'Login failed');
    }

    setIsLoading(false);
  };

  return (
    <div className="bg-gray-100 flex items-center justify-center min-h-screen">
      {/* Navbar */}
      <NavBar />

      {/* Login Card */}
      <div className="bg-white shadow-lg rounded-lg p-8 w-full max-w-md mt-20">
        {/* Logo + Header */}
        <div className="flex flex-col items-center mb-8">
          <img src="/logo.svg" alt="UNIfy logo" className="w-12 h-12 mb-2" />
          <h1 className="text-2xl font-bold">UNIfy</h1>
          <p className="text-gray-600 mt-2">Log in to your account</p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}


        {/* Login Form */}
        <form className="space-y-6" onSubmit={handleSubmit}>
          {/* Email */}
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-gray-700"
            >
              Email
            </label>
            <input
              type="email"
              id="email"
              name="email"
              required
              className="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-lime-500 focus:border-lime-500"
            />
          </div>

          {/* Password */}
          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700"
            >
              Password
            </label>
            <input
              type="password"
              id="password"
              name="password"
              required
              className="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-lime-500 focus:border-lime-500"
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="w-full bg-lime-500 hover:bg-lime-600 text-white font-semibold py-2 px-4 rounded-md transition"
          >
            Log In
          </button>

          {/* Optional links */}
          <div className="text-center mt-4">
            <a href="#" className="text-sm text-lime-600 hover:underline">
              Forgot password?
            </a>
          </div>
        </form>
      </div>
    </div>
  );
}
