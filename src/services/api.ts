/**
 * API service for UNIfy Flask backend integration
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export interface StudentProfile {
  mental_health: string;
  physical_health: string;
  courses: string;
  gpa: number;
  severity: 'mild' | 'moderate' | 'severe';
  /**
   * The student's first-choice school. Optional. When it names one of the 28
   * universities in the dataset, the response carries `preferred_match`.
   */
  preferred_university?: string;
}

export interface Evidence {
  accommodation: string;
  quote: string;
}

export interface University {
  name: string;
  score: number;
  accessibility_rating: number;
  disability_support_rating: number;
  available_accommodations: string[];
  location: string;
  reason: string;
  // Added with the grounded backend. Optional so older responses still typecheck.
  matched_accommodations?: string[];
  missing_accommodations?: string[];
  evidence?: Evidence[];
  // What the ratings actually count. They are coverage measures, not quality
  // judgments -- no one has rated these schools. Show this if you show a rating.
  rating_basis?: string;
}

/**
 * The student's own first-choice school, scored against the same 28-school
 * ranking. `rank` is its position out of `total_universities`, so a school that
 * misses the top five still comes back with a real, comparable standing.
 */
export interface PreferredMatch extends University {
  rank: number;
  total_universities: number;
  in_top_5: boolean;
}

export interface RecommendationResponse {
  success: boolean;
  // 'claude_grounded' | 'rule_based_grounded' | 'unavailable'
  source: string;
  model?: string | null;
  needed_accommodations: string[];
  needed_accommodation_ids?: string[];
  recommendations: University[];
  /** Null when no preference was given, or it isn't one of the 28 schools. */
  preferred_match?: PreferredMatch | null;
  grounding?: {
    universities_considered: number;
    extractor: string;
    extractor_quality: string;
    caveat: string;
  };
  error?: {
    code: string;
    message: string;
  };
}

/**
 * Get university recommendations from the Flask API
 */
export async function getRecommendations(profile: StudentProfile): Promise<RecommendationResponse> {
  try {
    console.log('API Base URL:', API_BASE_URL);
    console.log('Sending profile:', profile);

    const response = await fetch(`${API_BASE_URL}/api/recommendations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(profile),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error?.message || `HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

/**
 * Test the API connection
 */
export async function testAPI(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/test`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API Test Error:', error);
    throw error;
  }
}

/**
 * Get recommendations directly from Gemini AI
 */
export async function getGeminiRecommendations(profile: StudentProfile): Promise<RecommendationResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/gemini`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(profile),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error?.message || `HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Gemini API Error:', error);
    throw error;
  }
}

/**
 * Check API health
 */
export async function checkHealth(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Health Check Error:', error);
    throw error;
  }
}
