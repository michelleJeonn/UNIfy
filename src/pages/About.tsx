import NavBar from "../components/NavBar";

/**
 * About Us — Figma `About Us` frame (node 466:45).
 * Oversized headline, then the mission copy in a single measured column.
 */
export default function About() {
  return (
    <div className="min-h-screen bg-white text-black">
      <NavBar />

      <main className="mx-auto max-w-[1728px] px-6 pb-24 pt-[120px] md:px-10 lg:px-[182px] lg:pt-[200px]">
        <h1 className="text-[clamp(3rem,6vw,6.75rem)] leading-[1.08] tracking-[-0.02em]">
          About Us.
        </h1>

        <div className="mt-8 max-w-[1144px] space-y-6 text-[clamp(1rem,1.3vw,1.6875rem)] leading-relaxed">
          <p>
            At UNIfy, our mission is to remove barriers in the post-secondary
            journey by uniting accessibility, design, and technology into a
            single, intuitive platform. We build more than software—we craft
            guided, step-by-step experiences that demystify applications,
            scholarships, and disability-related accommodations for high school
            students in Ontario. Rooted in universal design, UNIfy offers
            adjustable text, dark mode, dyslexia-friendly fonts, and full
            keyboard navigation so every learner can move forward with
            confidence.
          </p>
          <p>
            Our work is shaped in collaboration with students, families,
            educators, guidance counselors, and disability services
            professionals. These partnerships ground our products in real
            needs—especially for youth with invisible or stigmatized
            disabilities—so that support plans are not only comprehensive but
            practical and timely. Behind UNIfy is a focused team of builders and
            advocates committed to clarity, dignity, and usability at every step.
          </p>
          <p>
            We believe accessibility should be seamless, not siloed. By
            providing an all-in-one SaaS platform that streamlines
            documentation, clarifies processes, and surfaces the right resources
            at the right moment, we empower students to access the
            accommodations they deserve—and to pursue the universities they
            dream of. At UNIfy, we’re not just organizing information; we’re
            opening doors to equitable opportunity in higher education.
          </p>
        </div>
      </main>
    </div>
  );
}
