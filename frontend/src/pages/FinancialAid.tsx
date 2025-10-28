import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import NavBar from "../components/NavBar";
import PageHeader from "../components/PageHeader";
import { getUniversityRoadmap, type StudentProfile, type RoadmapDetails } from "../services/api";

interface University {
  name: string;
  location: string;
}

export default function FinancialAid() {
  const navigate = useNavigate();
  const [selectedUniversity, setSelectedUniversity] = useState<University | null>(null);
  const [studentProfile, setStudentProfile] = useState<StudentProfile | null>(null);
  const [roadmapData, setRoadmapData] = useState<RoadmapDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Get selected university and student profile from sessionStorage
    const storedUniversity = sessionStorage.getItem('selectedUniversity');
    const storedProfile = sessionStorage.getItem('studentProfile');

    if (!storedUniversity || !storedProfile) {
      setError('No university or profile data found');
      setLoading(false);
      return;
    }

    try {
      const university = JSON.parse(storedUniversity);
      const profile = JSON.parse(storedProfile);
      
      setSelectedUniversity(university);
      setStudentProfile(profile);

      // Fetch roadmap data for this university
      getUniversityRoadmap(university.name, profile)
        .then(response => {
          if (response.success && response.roadmap) {
            setRoadmapData(response.roadmap);
          } else {
            setError(response.error?.message || 'Failed to load financial aid information');
          }
          setLoading(false);
        })
        .catch(err => {
          setError(err.message);
          setLoading(false);
        });
    } catch (error) {
      setError('Error parsing stored data');
      setLoading(false);
    }
  }, []);

  if (loading) {
    return (
      <div className="font-blmelody bg-white text-gray-900 min-h-screen">
        <NavBar />
        <main className="pt-32 pb-16 px-4 max-w-6xl mx-auto">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-lime-500 mx-auto mb-4"></div>
              <p>Loading financial aid information...</p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (error || !roadmapData || !selectedUniversity) {
    return (
      <div className="font-blmelody bg-white text-gray-900 min-h-screen">
        <NavBar />
        <main className="pt-32 pb-16 px-4 max-w-6xl mx-auto">
          <div className="text-center">
            <p className="text-red-600 mb-4">{error || 'No data available'}</p>
            <button
              onClick={() => navigate('/recommendations')}
              className="bg-lime-500 hover:bg-lime-600 text-white px-6 py-2 rounded-md"
            >
              Back to Recommendations
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
      <main className="pt-32 pb-16 px-4 max-w-6xl mx-auto">
        <PageHeader
          title={`Financial Aid - ${selectedUniversity.name}`}
          description="Explore available financial aid and grants for students with disabilities."
        />

        {/* Financial Aid Section */}
        <div className="space-y-8 mt-8">
          {/* Available Aid */}
          <div className="bg-green-50 border border-green-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4 text-green-900">Available Financial Aid</h3>
            {roadmapData.financial_aid.available_aids && roadmapData.financial_aid.available_aids.length > 0 ? (
              <ul className="space-y-2">
                {roadmapData.financial_aid.available_aids.map((aid, index) => (
                  <li key={index} className="flex items-start">
                    <span className="w-2 h-2 bg-green-400 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                    <span className="text-gray-800">{aid}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-600">No specific financial aid listed</p>
            )}
          </div>

          {/* Disability Grants */}
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4 text-purple-900">Disability-Specific Grants</h3>
            {roadmapData.financial_aid.disability_grants && roadmapData.financial_aid.disability_grants.length > 0 ? (
              <ul className="space-y-2">
                {roadmapData.financial_aid.disability_grants.map((grant, index) => (
                  <li key={index} className="flex items-start">
                    <span className="w-2 h-2 bg-purple-400 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                    <span className="text-gray-800">{grant}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-600">No specific disability grants listed</p>
            )}
          </div>

          {/* Application Process */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4 text-blue-900">Application Process</h3>
            <p className="text-gray-800 whitespace-pre-wrap">{roadmapData.financial_aid.application_process}</p>
          </div>

          {/* Additional Notes */}
          {roadmapData.financial_aid.notes && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold mb-2 text-yellow-900">Important Information</h3>
              <p className="text-gray-800 whitespace-pre-wrap">{roadmapData.financial_aid.notes}</p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex gap-4">
          <button
            onClick={() => navigate('/roadmap')}
            className="bg-lime-500 hover:bg-lime-600 text-white px-6 py-2 rounded-md"
          >
            Back to Roadmap
          </button>
          <button
            onClick={() => navigate('/recommendations')}
            className="bg-gray-500 hover:bg-gray-600 text-white px-6 py-2 rounded-md"
          >
            View All Recommendations
          </button>
        </div>
      </main>
    </div>
  );
}

