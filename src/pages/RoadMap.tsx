import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import NavBar from "../components/NavBar";
import type {
  RecommendationResponse,
  StudentProfile,
  University,
} from "../services/api";

/**
 * Roadmap — Figma `MacBook Pro 16" - 3` (node 45:62).
 *
 * A winding road runs down the page with checkpoint markers beside it, each
 * linking to its detail screen. The road's exact Figma coordinates are for a
 * fixed 1728×2028 artboard; positions here are expressed as percentages of the
 * road graphic so the layout survives real viewport widths.
 */

interface RoadmapData {
  studentProfile: StudentProfile;
  recommendations: RecommendationResponse;
  university?: University;
}

/** The three checkpoints the design places along the road, in order. */
const CHECKPOINTS = [
  { label: "Eligibility and Prerequisites", to: "/eligibility", top: "13%", side: "right" },
  { label: "Required Documents", to: "/required", top: "40%", side: "left" },
  { label: "Financial Aid", to: "/financial-aid", top: "67%", side: "right" },
] as const;

export default function RoadMap() {
  const navigate = useNavigate();
  const [roadmapData, setRoadmapData] = useState<RoadmapData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = sessionStorage.getItem("roadmapData");

    if (stored) {
      try {
        setRoadmapData(JSON.parse(stored) as RoadmapData);
        setLoading(false);
        return;
      } catch (error) {
        console.error("Error parsing roadmap data:", error);
      }
    }

    // Fall back to the recommendations run so a direct visit still works.
    const storedRecs = sessionStorage.getItem("recommendations");
    const storedProfile = sessionStorage.getItem("studentProfile");

    if (storedRecs && storedProfile) {
      try {
        const recommendations: RecommendationResponse = JSON.parse(storedRecs);
        setRoadmapData({
          recommendations,
          studentProfile: JSON.parse(storedProfile),
          university: recommendations.recommendations?.[0],
        });
        setLoading(false);
        return;
      } catch (error) {
        console.error("Error parsing stored data:", error);
      }
    }

    navigate("/information");
    setLoading(false);
  }, [navigate]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white text-black">
        <div className="text-center">
          <div className="mx-auto mb-4 size-24 animate-spin rounded-full border-b-2 border-unify-green" />
          <p>Loading your roadmap…</p>
        </div>
      </div>
    );
  }

  if (!roadmapData) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white text-black">
        <div className="text-center">
          <p>No roadmap data available. Please generate a new roadmap.</p>
          <button
            onClick={() => navigate("/information")}
            className="mt-4 h-[57px] cursor-pointer rounded-pill bg-unify-green px-7 text-[20px] transition hover:brightness-95"
          >
            Generate Roadmap
          </button>
        </div>
      </div>
    );
  }

  const universityName = roadmapData.university?.name ?? "your university";

  return (
    <div className="min-h-screen overflow-x-clip bg-white text-black">
      <NavBar />

      <main className="relative mx-auto max-w-[1728px] px-6 pb-24 pt-[120px] md:px-10 lg:px-[107px] lg:pt-[150px]">
        {/* Heading */}
        <div className="relative z-20 max-w-[662px]">
          <h1 className="text-[clamp(2.25rem,4vw,3.875rem)] leading-[1.11] tracking-[-0.02em]">
            Your step-by-step plan for {universityName}
          </h1>
          <p className="mt-4 text-[clamp(1rem,1.15vw,1.1875rem)]">
            Click on each Checkpoint for more details.
          </p>

          <button
            onClick={() => navigate("/recommendations")}
            className="group mt-8 inline-flex cursor-pointer items-center gap-4 rounded-[15px] px-5 py-3 text-[clamp(1rem,1.2vw,1.25rem)] ring-1 ring-black/15 transition hover:ring-black/35"
          >
            See my other university recommendations
            <span className="flex h-[30px] w-[80px] items-center justify-center rounded-[15px] bg-unify-green transition group-hover:brightness-95">
              <img
                src="/icons/arrow-polygon.svg"
                alt=""
                aria-hidden="true"
                className="h-[17px] w-[12px] rotate-90"
              />
            </span>
          </button>
        </div>

        {/* Road + checkpoints */}
        <div className="relative mt-10 lg:-mt-28">
          {/* The road is 806/1728 ≈ 47% of the design canvas and keeps its own
              996:3400 proportions. Centring it leaves room either side for the
              checkpoint markers, which alternate left and right. */}
          <div className="relative mx-auto aspect-[996/3400] w-[68%] max-w-[420px] lg:w-[47%] lg:max-w-[560px]">
            <img
              src="/icons/road-bg.svg"
              alt=""
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 size-full select-none"
            />
            <img
              src="/icons/road-dots.svg"
              alt=""
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 size-full select-none"
            />

            {CHECKPOINTS.map((c) => (
              <button
                key={c.to}
                onClick={() => navigate(c.to)}
                style={{ top: c.top }}
                className={`group absolute z-20 flex w-[130px] cursor-pointer flex-col items-center gap-3 md:w-[180px] ${
                  c.side === "right"
                    ? "left-full -translate-x-[8%]"
                    : "right-full translate-x-[8%]"
                }`}
              >
                <span
                  aria-hidden="true"
                  className="size-[72px] rounded-full border-[5px] border-dashed border-unify-green bg-white/70 transition group-hover:bg-unify-green-pale md:size-[100px]"
                />
                <span className="text-center text-[clamp(0.9375rem,1.15vw,1.1875rem)] leading-tight underline-offset-4 hover:underline">
                  {c.label}
                </span>
              </button>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
