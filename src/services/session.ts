import type {
  RecommendationResponse,
  StudentProfile,
  University,
} from "./api";

/**
 * Shape stashed in sessionStorage when a student picks a school to explore.
 * Written by the Recommendations screen, read by the roadmap and its
 * checkpoint detail screens.
 */
export interface RoadmapData {
  studentProfile: StudentProfile;
  recommendations: RecommendationResponse;
  university?: University;
}

/**
 * Read the current roadmap selection, falling back to the recommendations run
 * so a direct visit to a checkpoint page still renders.
 */
export function readRoadmapData(): RoadmapData | null {
  const stored = sessionStorage.getItem("roadmapData");
  if (stored) {
    try {
      return JSON.parse(stored) as RoadmapData;
    } catch (error) {
      console.error("Error parsing roadmap data:", error);
    }
  }

  const storedRecs = sessionStorage.getItem("recommendations");
  const storedProfile = sessionStorage.getItem("studentProfile");
  if (!storedRecs || !storedProfile) return null;

  try {
    const recommendations: RecommendationResponse = JSON.parse(storedRecs);
    return {
      recommendations,
      studentProfile: JSON.parse(storedProfile),
      university: recommendations.recommendations?.[0],
    };
  } catch (error) {
    console.error("Error parsing stored data:", error);
    return null;
  }
}
