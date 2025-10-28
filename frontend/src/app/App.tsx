import { Routes, Route } from "react-router-dom";
import Home from "../pages/Home";
import Login from "../pages/Login";
import UserInput from "../pages/UserInput";
import RoadMap from "../pages/RoadMap";
import Recommendations from "../pages/Recommendations";
import Eligibility from "../pages/Eligibility";
import RequiredDocs from "../pages/RequiredDocs";
import FinancialAid from "../pages/FinancialAid";
import Submission from "../pages/Submissions";
import Signup from "../pages/signup";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/information" element={<UserInput />} />
      <Route path="/roadmap" element={<RoadMap />} />
      <Route path="/recommendations" element={<Recommendations />} />
      <Route path="/eligibility" element={<Eligibility />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/required" element={<RequiredDocs />} />
      <Route path="/financial-aid" element={<FinancialAid />} />
      <Route path="/submission" element={<Submission />} />
    </Routes>
  );
}
