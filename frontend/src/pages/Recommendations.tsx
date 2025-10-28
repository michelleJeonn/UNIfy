import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import NavBar from "../components/NavBar";
import PageHeader from "../components/PageHeader";
import type { RecommendationResponse, StudentProfile, University } from "../services/api";

export default function Recommendations() {
  const navigate = useNavigate();
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [studentProfile, setStudentProfile] = useState<StudentProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get recommendations from sessionStorage
    const storedRecommendations = sessionStorage.getItem('recommendations');
    const storedProfile = sessionStorage.getItem('studentProfile');

    if (!storedRecommendations || !storedProfile) {
      // Redirect to user input if no data found
      navigate('/information');
      return;
    }

    try {
      setRecommendations(JSON.parse(storedRecommendations));
      setStudentProfile(JSON.parse(storedProfile));
    } catch (error) {
      console.error('Error parsing stored data:', error);
      navigate('/information');
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  if (loading) {
    return (
      <div className="font-blmelody bg-white text-gray-900 min-h-screen">
        <NavBar />
        <main className="pt-32 pb-16 px-4 max-w-5xl mx-auto">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-lime-500 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading recommendations...</p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (!recommendations || !studentProfile) {
    return (
      <div className="font-blmelody bg-white text-gray-900 min-h-screen">
        <NavBar />
        <main className="pt-32 pb-16 px-4 max-w-5xl mx-auto">
          <div className="text-center">
            <h2 className="text-2xl font-semibold mb-4">No Recommendations Found</h2>
            <p className="text-gray-600 mb-6">Please complete the user input form first.</p>
            <button
              onClick={() => navigate('/information')}
              className="bg-lime-500 hover:bg-lime-600 text-white px-6 py-2 rounded-md"
            >
              Go to User Input
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="font-blmelody bg-white text-gray-900 min-h-screen">
      {/* Navbar */}
      <NavBar />

      {/* Body */}
      <main className="pt-32 pb-16 px-4 max-w-5xl mx-auto">
        <PageHeader
          title="University Recommendations"
          description="Review alternative programs and institutions aligned with your academic and accessibility profile."
        />

        {/* Profile Summary */}
        <div className="bg-lime-50 border border-lime-200 rounded-md p-6 mb-8">
          <h3 className="text-lg font-semibold mb-4 text-lime-800">Your Profile Summary</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div><strong>Program:</strong> {studentProfile.courses}</div>
            <div><strong>GPA:</strong> {studentProfile.gpa}</div>
            <div><strong>Mental Health:</strong> {studentProfile.mental_health}</div>
            <div><strong>Physical Health:</strong> {studentProfile.physical_health}</div>
            <div><strong>Severity:</strong> {studentProfile.severity}</div>
            <div><strong>Recommendation Source:</strong> {recommendations.source}</div>
          </div>
        </div>

        {/* Needed Accommodations */}
        {recommendations.needed_accommodations && recommendations.needed_accommodations.length > 0 && (
          <div className="mb-8">
            <h3 className="text-xl font-semibold mb-4">Recommended Accommodations</h3>
            <div className="bg-blue-50 border border-blue-200 rounded-md p-6">
              <div className="flex flex-wrap gap-2">
                {recommendations.needed_accommodations.map((accommodation, index) => (
                  <span
                    key={index}
                    className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm"
                  >
                    {accommodation}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* University Recommendations */}
        <div>
          <h3 className="text-xl font-semibold mb-6">University Recommendations</h3>
          
          {recommendations.recommendations && recommendations.recommendations.length > 0 ? (
            <div className="space-y-6">
              {recommendations.recommendations.map((university: University, index: number) => (
                <div
                  key={index}
                  className="border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h4 className="text-lg font-semibold text-lime-700">{university.name}</h4>
                      <p className="text-gray-600">{university.location}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-lime-600">{university.score}/5</div>
                      <div className="text-sm text-gray-500">Overall Score</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                      <div className="text-sm text-gray-600">Accessibility Rating</div>
                      <div className="text-lg font-semibold">{university.accessibility_rating}/5</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Disability Support Rating</div>
                      <div className="text-lg font-semibold">{university.disability_support_rating}/5</div>
                    </div>
                  </div>

                  {university.reason && (
                    <div className="mb-4">
                      <div className="text-sm text-gray-600 mb-1">Why this university:</div>
                      <p className="text-gray-800">{university.reason}</p>
                    </div>
                  )}

                  {university.available_accommodations && university.available_accommodations.length > 0 && (
                    <div>
                      <div className="text-sm text-gray-600 mb-2">Available Accommodations:</div>
                      <div className="flex flex-wrap gap-2">
                        {university.available_accommodations.map((accommodation, accIndex) => (
                          <span
                            key={accIndex}
                            className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-sm"
                          >
                            {accommodation}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Generate Roadmap Button */}
                  <div className="mt-4">
                    <button
                      onClick={() => {
                        // Store selected university and navigate to roadmap
                        sessionStorage.setItem('selectedUniversity', JSON.stringify(university));
                        navigate('/roadmap');
                      }}
                      className="bg-lime-500 hover:bg-lime-600 text-white px-4 py-2 rounded-md transition"
                    >
                      Generate Roadmap
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="border border-lime-400 rounded-md p-8 min-h-[250px] flex items-center justify-center text-gray-400">
              <div className="text-center">
                <p className="mb-4">No specific recommendations available at this time.</p>
                <button
                  onClick={() => navigate('/information')}
                  className="bg-lime-500 hover:bg-lime-600 text-white px-6 py-2 rounded-md"
                >
                  Try Again
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Error Display */}
        {recommendations.error && (
          <div className="mt-8 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
            <strong>Error:</strong> {recommendations.error.message}
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-8 flex flex-col sm:flex-row gap-4">
          <button
            onClick={() => navigate('/information')}
            className="bg-gray-500 hover:bg-gray-600 text-white px-6 py-2 rounded-md"
          >
            Update Profile
          </button>
          <button
            onClick={() => navigate('/roadmap')}
            className="bg-lime-500 hover:bg-lime-600 text-white px-6 py-2 rounded-md"
          >
            View Roadmap
          </button>
        </div>
      </main>
    </div>
  );
}
