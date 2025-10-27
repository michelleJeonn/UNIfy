import NavBar from "../components/NavBar";
export default function About() {

    return (
        <div className="font-blmelody bg-white text-gray-900 min-h-screen">
              {/* Navbar */}
              <NavBar />

            <div className="max-w-4xl mx-auto px-6 py-12 mt-16">
                <h1 className="text-5xl md:text-6xl font-bold text-center mb-8 text-gray-900">
                    About Us
                </h1>
                <p className="text-lg leading-relaxed text-gray-700 text-justify md:text-left">
                    At UNIfy, our mission is to remove barriers in the post-secondary journey by uniting accessibility, design, and technology into a single, intuitive platform. We build more than software—we craft guided, step-by-step experiences that demystify applications, scholarships, and disability-related accommodations for high school students in Ontario. Rooted in universal design, UNify offers adjustable text, dark mode, dyslexia-friendly fonts, and full keyboard navigation so every learner can move forward with confidence. Our work is shaped in collaboration with students, families, educators, guidance counselors, and disability services professionals. These partnerships ground our products in real needs—especially for youth with invisible or stigmatized disabilities—so that support plans are not only comprehensive but practical and timely.
                </p>
                <p className="text-lg leading-relaxed text-gray-700 text-justify md:text-left mt-6">
                    We believe accessibility should be seamless, not siloed. By providing an all-in-one SaaS platform that streamlines documentation, clarifies processes, and surfaces the right resources at the right moment, we empower students to access the accommodations they deserve—and to pursue the universities they dream of. At UNify, we’re not just organizing information; we’re opening doors to equitable opportunity in higher education.
                </p>
            </div>
        </div>

    );
}