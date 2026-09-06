import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import NavBar from "../components/NavBar";
import ScoreGauge from "../components/ScoreGauge";
import StatTile from "../components/StatTile";
import type {
  RecommendationResponse,
  StudentProfile,
  University,
} from "../services/api";
import type { WizardAnswers } from "./UserInput";

/**
 * University Recommendations — Figma `MacBook Pro 16" - 10` (node 295:9).
 *
 * Headline, a three-card profile strip, the accommodation chips, then one
 * university card per recommendation: score gauge, three KPI tiles and a
 * "View Roadmap" action.
 */
export default function Recommendations() {
  const navigate = useNavigate();
  const [recommendations, setRecommendations] =
    useState<RecommendationResponse | null>(null);
  const [studentProfile, setStudentProfile] = useState<StudentProfile | null>(
    null
  );
  const [answers, setAnswers] = useState<WizardAnswers | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedRecommendations = sessionStorage.getItem("recommendations");
    const storedProfile = sessionStorage.getItem("studentProfile");
    const storedAnswers = sessionStorage.getItem("wizardAnswers");

    if (!storedRecommendations || !storedProfile) {
      navigate("/information");
      return;
    }

    try {
      setRecommendations(JSON.parse(storedRecommendations));
      setStudentProfile(JSON.parse(storedProfile));
      if (storedAnswers) setAnswers(JSON.parse(storedAnswers));
    } catch (error) {
      console.error("Error parsing stored data:", error);
      navigate("/information");
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  /** Hand the roadmap page everything it needs for the chosen school. */
  function viewRoadmap(university: University) {
    if (!studentProfile || !recommendations) return;
    sessionStorage.setItem(
      "roadmapData",
      JSON.stringify({ studentProfile, recommendations, university })
    );
    navigate("/roadmap");
  }

  if (loading) {
    return (
      <Shell>
        <div className="flex min-h-[400px] items-center justify-center">
          <div className="text-center">
            <div className="mx-auto mb-4 size-12 animate-spin rounded-full border-b-2 border-unify-green" />
            <p>Loading recommendations…</p>
          </div>
        </div>
      </Shell>
    );
  }

  if (!recommendations || !studentProfile) {
    return (
      <Shell>
        <div className="py-20 text-center">
          <h2 className="mb-4 text-[32px]">No Recommendations Found</h2>
          <p className="mb-6 text-black/70">
            Please complete the user input form first.
          </p>
          <button
            onClick={() => navigate("/information")}
            className="h-[57px] cursor-pointer rounded-pill bg-unify-green px-7 text-[20px] transition hover:brightness-95"
          >
            Go to User Input
          </button>
        </div>
      </Shell>
    );
  }

  const needed = recommendations.needed_accommodations ?? [];
  const list = recommendations.recommendations ?? [];
  const [top, ...rest] = list;

  return (
    <Shell>
      {/* Heading */}
      <h1 className="text-[clamp(2.5rem,5.2vw,5.25rem)] leading-[1.1] tracking-[-0.02em]">
        University Recommendations.
      </h1>
      <p className="mt-4 max-w-[1373px] text-[clamp(1rem,1.3vw,1.6875rem)] leading-snug">
        Review alternative programs and institutions aligned with your academic
        and accessibility profile.
      </p>
      <hr className="mt-8 border-0 border-t border-unify-rule" />

      {/* Profile strip */}
      <div className="mt-8 grid gap-4 md:grid-cols-3 lg:gap-[30px]">
        <ProfileCard>
          <div className="flex h-full flex-col items-center justify-center gap-4">
            <img
              src="/icons/account-circle.svg"
              alt=""
              aria-hidden="true"
              className="size-[110px] object-contain lg:size-[140px]"
            />
            <p className="text-[clamp(1.25rem,1.8vw,2rem)]">Your profile</p>
          </div>
        </ProfileCard>

        <ProfileCard>
          <dl className="space-y-3 text-[clamp(0.9375rem,1.15vw,1.25rem)]">
            <div>
              <dt className="font-semibold">Disability</dt>
              <dd>Mental | {studentProfile.mental_health}</dd>
              <dd>Physical | {studentProfile.physical_health}</dd>
            </div>
            <div>
              <dt className="inline font-semibold">Severity: </dt>
              <dd className="inline capitalize">{studentProfile.severity}</dd>
            </div>
          </dl>
        </ProfileCard>

        <ProfileCard>
          <dl className="space-y-3 text-[clamp(0.9375rem,1.15vw,1.25rem)]">
            <div>
              <dt className="inline font-semibold">GPA </dt>
              <dd className="inline">{studentProfile.gpa}</dd>
            </div>
            <div>
              <dt className="inline font-semibold">Program </dt>
              <dd className="inline">{studentProfile.courses}</dd>
            </div>
            <div>
              <dt className="font-semibold">Completed Courses</dt>
              <dd>
                {answers?.completedCourses.filter(Boolean).length
                  ? answers.completedCourses
                      .filter(Boolean)
                      .map((c) => c.split(" — ")[0])
                      .join(", ")
                  : "—"}
              </dd>
            </div>
          </dl>
        </ProfileCard>
      </div>

      {/* Accommodations */}
      {needed.length > 0 && (
        <section className="mt-10">
          <h2 className="text-[clamp(1rem,1.15vw,1.25rem)]">
            Recommended Accommodations
          </h2>
          <div className="mt-3 flex flex-wrap gap-3 rounded-[12px] bg-unify-blue-tint px-6 py-5">
            {needed.map((a) => (
              <span
                key={a}
                className="rounded-full bg-white/70 px-4 py-1.5 text-[clamp(0.8125rem,0.95vw,1rem)] text-unify-blue-deep"
              >
                {a}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Recommendations */}
      {list.length > 0 ? (
        <section className="mt-12 space-y-8">
          {top && (
            <UniversityCard
              university={top}
              neededCount={needed.length}
              onViewRoadmap={() => viewRoadmap(top)}
            />
          )}

          {rest.length > 0 && (
            <>
              <h2 className="pt-4 text-[clamp(1rem,1.15vw,1.25rem)]">
                Other University Recommendations
              </h2>
              {rest.map((u) => (
                <UniversityCard
                  key={u.name}
                  university={u}
                  neededCount={needed.length}
                  onViewRoadmap={() => viewRoadmap(u)}
                />
              ))}
            </>
          )}
        </section>
      ) : (
        <div className="mt-12 flex min-h-[250px] items-center justify-center rounded-card border border-unify-green/50 p-8">
          <div className="text-center">
            <p className="mb-4 text-black/60">
              No specific recommendations available at this time.
            </p>
            <button
              onClick={() => navigate("/information")}
              className="h-[57px] cursor-pointer rounded-pill bg-unify-green px-7 text-[20px] transition hover:brightness-95"
            >
              Try Again
            </button>
          </div>
        </div>
      )}

      {recommendations.error && (
        <div
          role="alert"
          className="mt-8 rounded-field border border-red-200 bg-red-50 px-4 py-3 text-red-800"
        >
          <strong>Error:</strong> {recommendations.error.message}
        </div>
      )}

      {/* Grounding caveat — the backend is explicit that ratings are coverage
          measures, not quality judgments. Keep that visible. */}
      {recommendations.grounding?.caveat && (
        <p className="mt-8 max-w-[1000px] text-[15px] leading-relaxed text-black/60">
          {recommendations.grounding.caveat}
        </p>
      )}

      <div className="mt-10 flex flex-col gap-4 sm:flex-row">
        <button
          onClick={() => navigate("/information")}
          className="h-[57px] cursor-pointer rounded-pill border border-black bg-white px-7 text-[20px] transition hover:bg-black/5"
        >
          Update Profile
        </button>
      </div>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white text-black">
      <NavBar />
      <main className="mx-auto max-w-[1728px] px-6 pb-20 pt-[120px] md:px-10 lg:px-[178px] lg:pt-[150px]">
        {children}
      </main>
    </div>
  );
}

function ProfileCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-[12px] bg-unify-green-tint p-6 lg:min-h-[240px]">
      {children}
    </div>
  );
}

function UniversityCard({
  university,
  neededCount,
  onViewRoadmap,
}: {
  university: University;
  neededCount: number;
  onViewRoadmap: () => void;
}) {
  // The API scores out of 5; the gauge in the design reads 0–100.
  const scorePct = Math.round((university.score / 5) * 100);

  const matched = university.matched_accommodations?.length;
  const accommodationsValue =
    matched !== undefined && neededCount > 0 ? `${matched}/${neededCount}` : "—";

  return (
    <article className="rounded-card border border-black/10 p-6 shadow-card md:p-10">
      <h3 className="text-[clamp(1.25rem,1.9vw,2rem)] font-semibold">
        {university.name}
        {university.location ? ` — ${university.location}` : ""}
      </h3>

      <div className="mt-6 flex flex-col items-center gap-6 lg:flex-row lg:items-stretch lg:gap-10">
        <ScoreGauge
          value={scorePct}
          label={`Match score for ${university.name}`}
        />

        <div className="flex w-full flex-1 flex-wrap gap-4">
          <StatTile
            tone="pale"
            label="GPA requirement"
            value="—"
            title="Program GPA cut-offs aren't returned by /api/recommendations yet."
          />
          <StatTile
            tone="green"
            label="Prerequisites"
            value="—"
            title="Course prerequisites aren't returned by /api/recommendations yet."
          />
          <StatTile
            tone="blue"
            label="Accommodations"
            value={accommodationsValue}
            title={
              university.rating_basis ??
              "Needed accommodations evidenced in this school's published materials."
            }
          />
        </div>
      </div>

      {university.reason && (
        <p className="mt-6 text-[clamp(0.9375rem,1.05vw,1.125rem)] leading-relaxed text-black/75">
          {university.reason}
        </p>
      )}

      <button
        onClick={onViewRoadmap}
        className="group mt-6 inline-flex cursor-pointer items-center gap-4"
      >
        <span className="text-[clamp(1rem,1.3vw,1.625rem)]">View Roadmap</span>
        <span className="flex h-[30px] w-[130px] items-center justify-center rounded-[15px] bg-unify-green transition group-hover:brightness-95">
          <img
            src="/icons/arrow-polygon.svg"
            alt=""
            aria-hidden="true"
            className="h-[17px] w-[12px] rotate-90"
          />
        </span>
      </button>
    </article>
  );
}
