import { useEffect, useState } from "react";
import NavBar from "../components/NavBar";
import PageHeader, {
  CheckpointSection,
  NoData,
} from "../components/PageHeader";
import { readRoadmapData, type RoadmapData } from "../services/session";

/**
 * Eligibility and Prerequisites — Figma `MacBook Pro 16" - 15` (node 558:277).
 *
 * The design's hairline-separated section list, filled from the student's
 * profile and the selected school where the API provides the data.
 */
export default function Eligibility() {
  const [data, setData] = useState<RoadmapData | null>(null);

  useEffect(() => {
    setData(readRoadmapData());
  }, []);

  const profile = data?.studentProfile;
  const university = data?.university;

  return (
    <div className="min-h-screen bg-white text-black">
      <NavBar />

      <main className="mx-auto max-w-[1728px] px-6 pb-20 pt-[120px] md:px-10 lg:px-[96px] lg:pt-[150px]">
        <PageHeader
          title="Eligibility and Prerequisites"
          description={
            university
              ? `What ${university.name} expects from applicants.`
              : "Let’s see if you meet the minimum requirements for your target programs."
          }
        />

        <CheckpointSection label="Your Academic Profile">
          {profile ? (
            <dl className="grid gap-x-10 gap-y-2 sm:grid-cols-2">
              <div>
                <dt className="inline font-semibold">GPA: </dt>
                <dd className="inline">{profile.gpa}</dd>
              </div>
              <div>
                <dt className="inline font-semibold">Program area: </dt>
                <dd className="inline">{profile.courses}</dd>
              </div>
            </dl>
          ) : (
            <NoData note="Complete the information form to see your profile here." />
          )}
        </CheckpointSection>

        <CheckpointSection label="Anticipated Admission Range">
          <NoData note="Not available — /api/recommendations doesn’t return program GPA cut-offs yet, though data/clean/programs.csv holds them." />
        </CheckpointSection>

        <CheckpointSection label="Required Courses">
          <NoData note="Not available — course prerequisites aren’t exposed by the API yet, though data/clean/programs.csv holds them per program." />
        </CheckpointSection>

        <CheckpointSection label="Accessibility Fit">
          {university?.matched_accommodations?.length ? (
            <>
              <p className="font-semibold">Evidenced at this school</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {university.matched_accommodations.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>

              {university.missing_accommodations?.length ? (
                <>
                  <p className="mt-6 font-semibold">Not evidenced</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-black/70">
                    {university.missing_accommodations.map((a) => (
                      <li key={a}>{a}</li>
                    ))}
                  </ul>
                </>
              ) : null}
            </>
          ) : (
            <NoData note="Pick a university from your recommendations to see how its accommodations line up." />
          )}
        </CheckpointSection>

        <div className="border-t border-unify-rule" />
      </main>
    </div>
  );
}
