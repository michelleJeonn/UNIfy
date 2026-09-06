import { useEffect, useState } from "react";
import NavBar from "../components/NavBar";
import PageHeader, {
  CheckpointSection,
  NoData,
} from "../components/PageHeader";
import { readRoadmapData, type RoadmapData } from "../services/session";

/**
 * Financial Aid — Figma `MacBook Pro 16" - 17` (node 585:1029).
 *
 * The third checkpoint on the roadmap. New in this design; it reuses the
 * checkpoint detail layout shared with Eligibility and Required Documents.
 */
export default function FinancialAid() {
  const [data, setData] = useState<RoadmapData | null>(null);

  useEffect(() => {
    setData(readRoadmapData());
  }, []);

  const university = data?.university;

  return (
    <div className="min-h-screen bg-white text-black">
      <NavBar />

      <main className="mx-auto max-w-[1728px] px-6 pb-20 pt-[120px] md:px-10 lg:px-[96px] lg:pt-[150px]">
        <PageHeader
          title="Financial Aid"
          description={
            university
              ? `Funding routes available at ${university.name}.`
              : "Grants, bursaries and OSAP routes for your shortlist."
          }
        />

        <CheckpointSection label="OSAP Eligibility">
          <NoData note="Not available — data/clean/universities.csv has an osap_eligibility column, but /api/recommendations doesn’t return it yet." />
        </CheckpointSection>

        <CheckpointSection label="Bursaries and Grants">
          <NoData note="Not available — the dataset’s bursaries column isn’t exposed by the API yet." />
        </CheckpointSection>

        <CheckpointSection label="Deadlines">
          <NoData note="Not available — no deadline data exists in the dataset or the API." />
        </CheckpointSection>

        <div className="border-t border-unify-rule" />
      </main>
    </div>
  );
}
