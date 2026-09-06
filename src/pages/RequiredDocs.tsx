import { useEffect, useState } from "react";
import NavBar from "../components/NavBar";
import PageHeader, {
  CheckpointSection,
  NoData,
} from "../components/PageHeader";
import { readRoadmapData, type RoadmapData } from "../services/session";

/**
 * Required Documents — Figma `MacBook Pro 16" - 16` (node 585:1011), which
 * shares the checkpoint detail layout with Eligibility and Financial Aid.
 */
export default function RequiredDocs() {
  const [data, setData] = useState<RoadmapData | null>(null);

  useEffect(() => {
    setData(readRoadmapData());
  }, []);

  const university = data?.university;
  const needed = data?.recommendations?.needed_accommodations ?? [];

  return (
    <div className="min-h-screen bg-white text-black">
      <NavBar />

      <main className="mx-auto max-w-[1728px] px-6 pb-20 pt-[120px] md:px-10 lg:px-[96px] lg:pt-[150px]">
        <PageHeader
          title="Required Documents"
          description={
            university
              ? `What ${university.name} asks you to submit to register with accessibility services.`
              : "Let’s make sure you have the right documents to access accommodations at each school."
          }
        />

        <CheckpointSection label="Accommodations You’re Registering For">
          {needed.length ? (
            <ul className="list-disc space-y-1 pl-5">
              {needed.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          ) : (
            <NoData note="Complete the information form to see the accommodations matched to your profile." />
          )}
        </CheckpointSection>

        <CheckpointSection label="Required Documents">
          <NoData note="Not available — data/clean/universities.csv has a documentation_requirements column, but /api/recommendations doesn’t return it yet." />
        </CheckpointSection>

        <CheckpointSection label="Step-by-step Guide">
          <NoData note="Not available — the registration_process and documentation_submission columns exist in the dataset but aren’t exposed by the API yet." />
        </CheckpointSection>

        <div className="border-t border-unify-rule" />
      </main>
    </div>
  );
}
