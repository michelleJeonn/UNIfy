import { useEffect, useState } from "react";
import NavBar from "../components/NavBar";
import PageHeader, {
  CheckpointSection,
  NoData,
} from "../components/PageHeader";
import { readRoadmapData, type RoadmapData } from "../services/session";

/**
 * Application Submission Steps.
 *
 * NOTE: the redesigned roadmap (node 45:62) drops this checkpoint in favour of
 * Financial Aid, so nothing links here any more. The route is kept so existing
 * links and bookmarks keep working, restyled to the shared checkpoint layout.
 */
export default function Submission() {
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
          title="Application Submission Steps"
          description={
            university
              ? `Getting your application to ${university.name} in on time.`
              : "Let’s get your applications and accommodations submitted on time."
          }
        />

        <CheckpointSection label="Submission Checklist">
          <NoData note="Not available — no submission-step data exists in the dataset or the API." />
        </CheckpointSection>

        <div className="border-t border-unify-rule" />
      </main>
    </div>
  );
}
