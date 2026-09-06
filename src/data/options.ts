/**
 * Option lists backing the "Enter your information" wizard dropdowns.
 *
 * The Figma dropdown symbols (`GPA list` 426:60, `School list` 585:575) show
 * the control but not a data source, so these are sourced from the datasets the
 * Flask backend actually ranks over — data/clean/universities.csv (28 Ontario
 * universities) — and from the option sets the API already accepts.
 */

/** 4.0 → 1.0 in 0.1 steps. The API validates gpa into [0.0, 4.0]. */
export const GPA_OPTIONS: string[] = Array.from({ length: 31 }, (_, i) =>
  (4.0 - i * 0.1).toFixed(1)
);

/** The 28 universities in data/clean/universities.csv, in dataset order. */
export const UNIVERSITY_OPTIONS = [
  "University of Toronto St.George",
  "University of Toronto Mississauga",
  "University of Toronto Scarborough",
  "University of Waterloo",
  "McMaster University",
  "TMU",
  "York University (Keele)",
  "York University (Glendon)",
  "York University (Markham)",
  "Queen's University",
  "OCAD University",
  "University of Guelph",
  "University of Guelph-Humber",
  "Wilfrid Laurier University",
  "University of Ottawa",
  "Algoma University",
  "Brock University",
  "Carleton University",
  "Lakehead University",
  "Laurentian University",
  "Nipissing University",
  "Ontario Tech University",
  "Trent University",
  "Trent University (Durham GTA)",
  "University of Windsor",
  // Curly apostrophe, matching data/clean/universities.csv exactly.
  "Université de l’Ontario français",
  "Western University (Main Campus)",
  "Western University (Affiliated University Colleges)",
];

/**
 * Program areas. Sent to the API as `courses`; this is the same curated list
 * the pre-redesign form used, kept so the backend contract is unchanged.
 * (data/clean/programs.csv has 1,579 distinct program names — too many for a
 * single select, and the API matches on broad area, not exact program.)
 */
export const PROGRAM_OPTIONS = [
  "Computer Science",
  "Engineering",
  "Business",
  "Psychology",
  "Biology",
  "Medicine",
  "Arts",
  "Education",
  "Other",
];

/** Common Ontario 4U/4M courses, matching the codes shown on the Eligibility frame. */
export const COURSE_OPTIONS = [
  "ENG4U — English",
  "MHF4U — Advanced Functions",
  "MCV4U — Calculus and Vectors",
  "MDM4U — Mathematics of Data Management",
  "SBI4U — Biology",
  "SCH4U — Chemistry",
  "SPH4U — Physics",
  "ICS4U — Computer Science",
  "SES4U — Earth and Space Science",
  "BAT4M — Financial Accounting",
  "CGW4U — World Issues",
  "CHY4U — World History",
  "FSF4U — Core French",
  "AVI4M — Visual Arts",
  "HHS4U — Families in Canada",
  "HZT4U — Philosophy",
];

export const FINANCIAL_OPTIONS = [
  "OSAP eligible",
  "Need-based bursaries",
  "Entrance scholarships",
  "Work-study / co-op earnings",
  "No financial support needed",
];

export const PHYSICAL_HEALTH_OPTIONS = [
  "None",
  "Mobility Impairment",
  "Visual Impairment",
  "Hearing Impairment",
  "Chronic Illness",
  "Other",
];

export const MENTAL_HEALTH_OPTIONS = [
  "None",
  "ADHD",
  "Anxiety",
  "Depression",
  "Autism Spectrum Disorder",
  "Learning Disability",
  "Other",
];

export const SEVERITY_OPTIONS = [
  { value: "mild", label: "Mild" },
  { value: "moderate", label: "Moderate" },
  { value: "severe", label: "Severe" },
] as const;

/** The three steps of the "Enter your information" wizard, in order. */
export const WIZARD_STEPS = [
  "Academic Profile",
  "University Preferences",
  "Accessibility & Support",
] as const;
