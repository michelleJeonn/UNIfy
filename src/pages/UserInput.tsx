import { useState } from "react";
import { useNavigate } from "react-router-dom";
import NavBar from "../components/NavBar";
import WizardSidebar from "../components/WizardSidebar";
import {
  AddMore,
  FieldLabel,
  PillButton,
  RingRadio,
  Select,
  TextArea,
} from "../components/FormControls";
import {
  COURSE_OPTIONS,
  FINANCIAL_OPTIONS,
  GPA_OPTIONS,
  MENTAL_HEALTH_OPTIONS,
  PHYSICAL_HEALTH_OPTIONS,
  PROGRAM_OPTIONS,
  SEVERITY_OPTIONS,
  UNIVERSITY_OPTIONS,
  WIZARD_STEPS,
} from "../data/options";
import { getRecommendations, type StudentProfile } from "../services/api";

/**
 * "Enter your information" — Figma nodes 313:2 (Academic Profile),
 * 335:26 (University Preferences) and 342:96 (Accessibility & Support).
 *
 * The pre-redesign page was one long form; the design splits it into three
 * steps behind a shared sidebar. The submit path is unchanged: it still builds
 * a StudentProfile, POSTs it via getRecommendations(), stashes the result in
 * sessionStorage and routes to /recommendations.
 */

export type WizardAnswers = {
  gpa: string;
  completedCourses: string[];
  extracurriculars: string;
  universities: string[];
  programs: string[];
  applicationRound: string;
  financialPreference: string;
  disabilityType: string;
  physicalHealth: string;
  mentalHealth: string;
  severity: string;
};

const INITIAL: WizardAnswers = {
  gpa: "",
  completedCourses: [""],
  extracurriculars: "",
  universities: [""],
  programs: [""],
  applicationRound: "",
  financialPreference: "",
  disabilityType: "",
  physicalHealth: "",
  mentalHealth: "",
  severity: "",
};

export default function UserInput() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<WizardAnswers>(INITIAL);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  function set<K extends keyof WizardAnswers>(key: K, value: WizardAnswers[K]) {
    setAnswers((a) => ({ ...a, [key]: value }));
    setValidationError(null);
  }

  function setAt(key: "completedCourses" | "universities" | "programs", i: number, value: string) {
    setAnswers((a) => {
      const next = [...a[key]];
      next[i] = value;
      return { ...a, [key]: next };
    });
    setValidationError(null);
  }

  function addAt(key: "completedCourses" | "universities" | "programs") {
    setAnswers((a) => ({ ...a, [key]: [...a[key], ""] }));
  }

  /** Per-step gating so a half-filled profile never reaches the API. */
  function validateStep(i: number): string | null {
    if (i === 0 && !answers.gpa) return "Please select your current GPA.";
    if (i === 1 && !answers.programs.some(Boolean))
      return "Please choose at least one program.";
    if (i === 2 && !answers.severity)
      return "Please select how much support you need.";
    return null;
  }

  function goNext() {
    const problem = validateStep(step);
    if (problem) {
      setValidationError(problem);
      return;
    }
    setValidationError(null);
    setStep((s) => Math.min(s + 1, WIZARD_STEPS.length - 1));
  }

  function goBack() {
    setValidationError(null);
    setStep((s) => Math.max(s - 1, 0));
  }

  async function handleSubmit() {
    const problem = validateStep(2);
    if (problem) {
      setValidationError(problem);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Map the wizard's answers onto the profile shape the Flask API validates.
      const profile: StudentProfile = {
        mental_health: answers.mentalHealth || "None",
        physical_health: answers.physicalHealth || "None",
        courses: answers.programs.find(Boolean) || "General",
        gpa: parseFloat(answers.gpa) || 3.0,
        // The select shows "Mild"/"Moderate"/"Severe"; the API validates lowercase.
        severity:
          (answers.severity.toLowerCase() as StudentProfile["severity"]) ||
          "moderate",
      };

      const result = await getRecommendations(profile);

      sessionStorage.setItem("recommendations", JSON.stringify(result));
      sessionStorage.setItem("studentProfile", JSON.stringify(profile));
      // The design's profile strip shows completed courses and program choices,
      // which aren't part of the API payload — keep them for that screen.
      sessionStorage.setItem("wizardAnswers", JSON.stringify(answers));

      navigate("/recommendations");
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-white text-black">
      <NavBar />

      <main className="mx-auto flex max-w-[1728px] flex-col gap-8 px-6 pb-16 pt-[110px] md:px-8 lg:flex-row lg:items-stretch lg:gap-[27px] lg:px-[27px] lg:pt-[115px]">
        <WizardSidebar
          currentStep={step}
          onStepChange={(i) => {
            setValidationError(null);
            setStep(i);
          }}
        />

        {/* Step card */}
        <section
          aria-label={WIZARD_STEPS[step]}
          className="flex w-full flex-col rounded-card bg-white p-6 shadow-panel md:p-10 lg:min-h-[856px] lg:flex-1 lg:p-[46px]"
        >
          <div className="flex-1 space-y-8">
            {step === 0 && (
              <>
                <div>
                  <FieldLabel htmlFor="gpa">Current GPA:</FieldLabel>
                  <div className="mt-3">
                    <Select
                      id="gpa"
                      name="gpa"
                      value={answers.gpa}
                      onChange={(e) => set("gpa", e.target.value)}
                      options={GPA_OPTIONS}
                      placeholder="Select GPA"
                      centered
                      required
                    />
                  </div>
                </div>

                <div>
                  <FieldLabel htmlFor="course-0">
                    Completed High School Courses:
                  </FieldLabel>
                  <div className="mt-3 space-y-3">
                    {answers.completedCourses.map((value, i) => (
                      <Select
                        key={i}
                        id={`course-${i}`}
                        name={`completedCourses[${i}]`}
                        value={value}
                        onChange={(e) => setAt("completedCourses", i, e.target.value)}
                        options={COURSE_OPTIONS}
                        placeholder="Select a course"
                      />
                    ))}
                  </div>
                  <AddMore onClick={() => addAt("completedCourses")} />
                </div>

                <div>
                  <FieldLabel htmlFor="extracurriculars">
                    List of Extracurriculars (Optional)
                  </FieldLabel>
                  <div className="mt-3">
                    <TextArea
                      id="extracurriculars"
                      name="extracurriculars"
                      value={answers.extracurriculars}
                      onChange={(e) => set("extracurriculars", e.target.value)}
                      rows={6}
                    />
                  </div>
                </div>
              </>
            )}

            {step === 1 && (
              <>
                <div>
                  <FieldLabel htmlFor="university-0">University Choices:</FieldLabel>
                  <div className="mt-3 space-y-3">
                    {answers.universities.map((value, i) => (
                      <Select
                        key={i}
                        id={`university-${i}`}
                        name={`universities[${i}]`}
                        value={value}
                        onChange={(e) => setAt("universities", i, e.target.value)}
                        options={UNIVERSITY_OPTIONS}
                        placeholder="Select University"
                        centered={i === 0}
                      />
                    ))}
                  </div>
                  <AddMore onClick={() => addAt("universities")} />
                </div>

                <div>
                  <FieldLabel htmlFor="program-0">Program Choices:</FieldLabel>
                  <div className="mt-3 space-y-3">
                    {answers.programs.map((value, i) => (
                      <Select
                        key={i}
                        id={`program-${i}`}
                        name={`programs[${i}]`}
                        value={value}
                        onChange={(e) => setAt("programs", i, e.target.value)}
                        options={PROGRAM_OPTIONS}
                        placeholder="Select a program"
                      />
                    ))}
                  </div>
                  <AddMore onClick={() => addAt("programs")} />
                </div>

                <fieldset>
                  <legend className="text-[clamp(1.5rem,2.6vw,2.6875rem)] leading-tight tracking-[-0.02em] text-unify-green-dark">
                    Application Round (Early/General Round):
                  </legend>
                  <div className="mt-4 flex flex-wrap gap-x-[80px] gap-y-4 lg:gap-x-[380px]">
                    {["Early", "General"].map((round) => (
                      <RingRadio
                        key={round}
                        name="applicationRound"
                        value={round}
                        label={round}
                        checked={answers.applicationRound === round}
                        onChange={() => set("applicationRound", round)}
                      />
                    ))}
                  </div>
                </fieldset>

                <div>
                  <FieldLabel htmlFor="financial">Financial Preferences:</FieldLabel>
                  <div className="mt-3">
                    <Select
                      id="financial"
                      name="financialPreference"
                      value={answers.financialPreference}
                      onChange={(e) => set("financialPreference", e.target.value)}
                      options={FINANCIAL_OPTIONS}
                      placeholder="Select a preference"
                    />
                  </div>
                </div>
              </>
            )}

            {step === 2 && (
              <>
                <fieldset>
                  <legend className="text-[clamp(1.5rem,2.6vw,2.6875rem)] leading-tight tracking-[-0.02em] text-unify-green-dark">
                    Type of Disability:
                  </legend>
                  <div className="mt-4 flex flex-wrap gap-x-10 gap-y-4 lg:gap-x-[130px]">
                    {[
                      "Physical",
                      "Neurodevelopmental/Mental Health",
                      "Both",
                    ].map((type) => (
                      <RingRadio
                        key={type}
                        name="disabilityType"
                        value={type}
                        label={type}
                        checked={answers.disabilityType === type}
                        onChange={() => set("disabilityType", type)}
                      />
                    ))}
                  </div>
                </fieldset>

                <div>
                  <FieldLabel htmlFor="physical">Physical Disabilities:</FieldLabel>
                  <div className="mt-3">
                    <Select
                      id="physical"
                      name="physicalHealth"
                      value={answers.physicalHealth}
                      onChange={(e) => set("physicalHealth", e.target.value)}
                      options={PHYSICAL_HEALTH_OPTIONS}
                      placeholder="Select a condition"
                    />
                  </div>
                </div>

                <div>
                  <FieldLabel htmlFor="mental">
                    Neurodevelopmental/Mental Health Conditions:
                  </FieldLabel>
                  <div className="mt-3">
                    <Select
                      id="mental"
                      name="mentalHealth"
                      value={answers.mentalHealth}
                      onChange={(e) => set("mentalHealth", e.target.value)}
                      options={MENTAL_HEALTH_OPTIONS}
                      placeholder="Select a condition"
                    />
                  </div>
                </div>

                {/*
                  Not present in the Figma design, but /api/recommendations
                  rejects a profile without `severity`. Styled to match the
                  surrounding fields.
                */}
                <div>
                  <FieldLabel htmlFor="severity">Level of Support Needed:</FieldLabel>
                  <div className="mt-3">
                    <Select
                      id="severity"
                      name="severity"
                      value={answers.severity}
                      onChange={(e) => set("severity", e.target.value)}
                      options={SEVERITY_OPTIONS.map((s) => s.label)}
                      placeholder="Select a level"
                      required
                    />
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Status + step navigation */}
          <div className="mt-8 space-y-4">
            {validationError && (
              <p role="alert" className="text-[18px] text-red-600">
                {validationError}
              </p>
            )}

            {error && (
              <div
                role="alert"
                className="rounded-field border border-red-200 bg-red-50 px-4 py-3 text-red-800"
              >
                {error}
              </div>
            )}

            {isLoading && (
              <div className="rounded-field border border-unify-green/40 bg-unify-green-pale px-4 py-3 text-unify-green-dark">
                Getting your personalized recommendations…
              </div>
            )}

            <div className="flex items-center justify-between gap-4">
              {step > 0 ? (
                <PillButton onClick={goBack}>Back</PillButton>
              ) : (
                <span />
              )}

              {step < WIZARD_STEPS.length - 1 ? (
                <PillButton onClick={goNext}>Next</PillButton>
              ) : (
                <PillButton onClick={handleSubmit} disabled={isLoading}>
                  {isLoading ? "Generating…" : "Generate my roadmap!"}
                </PillButton>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
