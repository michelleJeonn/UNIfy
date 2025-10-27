import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import NavBar from "../components/NavBar";
import { getRecommendations, type StudentProfile } from "../services/api";

export default function UserInput() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const formData = new FormData(e.currentTarget);

      // Create student profile from form data
      const profile: StudentProfile = {
        mental_health: formData.get('mental-health')?.toString() || 'None',
        physical_health: formData.get('physical-health')?.toString() || 'None',
        courses: formData.get('courses')?.toString() || 'General',
        gpa: parseFloat(formData.get('gpa')?.toString() || '3.0'),
        severity: (formData.get('severity')?.toString() as 'mild' | 'moderate' | 'severe') || 'moderate'
      };

      console.log('Form submitted with profile:', profile);

      // Get recommendations from API
      const result = await getRecommendations(profile);

      // Store recommendations in sessionStorage for the recommendations page
      sessionStorage.setItem('recommendations', JSON.stringify(result));
      sessionStorage.setItem('studentProfile', JSON.stringify(profile));

      // Navigate to recommendations page
      navigate("/recommendations");

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="font-blmelody bg-white text-gray-900 min-h-screen">
      {/* Navbar */}
      <NavBar />

      {/* Form Section */}
      <section className="pt-32 pb-16 px-4 max-w-3xl mx-auto">
        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}
        <h2 className="text-3xl mb-2">Let’s personalize your journey.</h2>
        <p className="mb-8 text-gray-600">
          Tell us a bit about your academic background and accessibility needs
          so we can build your custom university admissions roadmap.
        </p>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="space-y-6 bg-white p-8 rounded shadow"
        >
          {/* Full Name */}
          <div>
            <label
              htmlFor="name"
              className="block text-sm font-medium mb-1 text-lime-600"
            >
              Full Name
            </label>
            <input
              id="name"
              name="name"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-lime-500 focus:border-lime-500"
            />
          </div>

          {/* Email */}
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium mb-1 text-lime-600"
            >
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-lime-500 focus:border-lime-500"
            />
          </div>

          {/* High School */}
          <div>
            <label
              htmlFor="school"
              className="block text-sm font-medium mb-1 text-lime-600"
            >
              High School
            </label>
            <input
              id="school"
              name="school"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-lime-500 focus:border-lime-500"
            />
          </div>

          {/* GPA */}
          <div>
            <label
              htmlFor="gpa"
              className="block text-sm font-medium mb-1 text-lime-600"
            >
              Current GPA
            </label>
            <input
              id="gpa"
              name="gpa"
              type="number"
              step="0.1"
              max={4.0}
              min={0.0}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-lime-500 focus:border-lime-500"
            />
          </div>

          {/* Program of Interest */}
          <div>
            <label
              htmlFor="program"
              className="block text-sm font-medium mb-1 text-lime-600"
            >
              Program of Interest
            </label>
            <input
              id="program"
              name="program"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-lime-500 focus:border-lime-500"
            />
          </div>


          {/* University Preference */}
          <div>
            <label className="block text-sm font-medium mb-2 text-lime-600">
              University Preference
            </label>
            <input
              id="university"
              name="university"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-lime-500 focus:border-lime-500"
            />
          </div>

          {/* Application Round */}
          <fieldset>
            <legend className="block text-sm font-medium mb-1 text-lime-600">
              Application Round (Early/General Round)
            </legend>
            <div className="flex flex-wrap gap-6">
              <label className="inline-flex items-center gap-2">
                <input type="radio" name="app-round" value="Early" />
                Early
              </label>
              <label className="inline-flex items-center gap-2">
                <input type="radio" name="app-round" value="General" /> General
              </label>
            </div>
          </fieldset>

          {/* Extracurriculars */}
          <div>
            <label
              htmlFor="ecs"
              className="block text-sm font-medium mb-1 text-lime-600"
            >
              List of Extracurriculars (Optional)
            </label>
            <textarea
              id="ecs"
              name="ecs"
              rows={4}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-lime-500 focus:border-lime-500"
            />
          </div>

          {/* Mental Health Condition */}
          <div>
            <label
              htmlFor="mental-health"
              className="block text-sm font-medium mb-1 text-lime-600"
            >
              Mental Health Condition
            </label>
            <select
              id="mental-health"
              name="mental-health"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-lime-500 focus:border-lime-500"
            >
              <option value="None">None</option>
              <option value="ADHD">ADHD</option>
              <option value="Anxiety">Anxiety</option>
              <option value="Depression">Depression</option>
              <option value="Autism">Autism Spectrum Disorder</option>
              <option value="Learning Disability">Learning Disability</option>
              <option value="Other">Other</option>
            </select>
          </div>

          {/* Physical Health Condition */}
          <div>
            <label
              htmlFor="physical-health"
              className="block text-sm font-medium mb-1 text-lime-600"
            >
              Physical Health Condition
            </label>
            <select
              id="physical-health"
              name="physical-health"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-lime-500 focus:border-lime-500"
            >
              <option value="None">None</option>
              <option value="Mobility Impairment">Mobility Impairment</option>
              <option value="Visual Impairment">Visual Impairment</option>
              <option value="Hearing Impairment">Hearing Impairment</option>
              <option value="Chronic Illness">Chronic Illness</option>
              <option value="Other">Other</option>
            </select>
          </div>

          {/* Severity Level */}
          <fieldset>
            <legend className="block text-sm font-medium mb-1 text-lime-600">
              Severity Level
            </legend>
            <div className="flex flex-wrap gap-6">
              <label className="inline-flex items-center gap-2">
                <input type="radio" name="severity" value="mild" required />
                Mild
              </label>
              <label className="inline-flex items-center gap-2">
                <input type="radio" name="severity" value="moderate" required />
                Moderate
              </label>
              <label className="inline-flex items-center gap-2">
                <input type="radio" name="severity" value="severe" required />
                Severe
              </label>
            </div>
          </fieldset>

          {/* Program of Interest */}
          <div>
            <label
              htmlFor="program-interest"
              className="block text-sm font-medium mb-1 text-lime-600"
            >
              Program of Interest
            </label>
            <select
              id="program-interest"
              name="courses"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-lime-500 focus:border-lime-500"
            >
              <option value="">Select a program</option>
              <option value="Computer Science">Computer Science</option>
              <option value="Engineering">Engineering</option>
              <option value="Business">Business</option>
              <option value="Psychology">Psychology</option>
              <option value="Biology">Biology</option>
              <option value="Medicine">Medicine</option>
              <option value="Arts">Arts</option>
              <option value="Education">Education</option>
              <option value="Other">Other</option>
            </select>
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
              {error}
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-md">
              Getting your personalized recommendations...
            </div>
          )}




          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-lime-500 hover:bg-lime-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-md transition"
          >
            {isLoading ? "Getting Recommendations..." : "Get Recommendations"}
          </button>
        </form>
      </section>
    </div>
  );
}
