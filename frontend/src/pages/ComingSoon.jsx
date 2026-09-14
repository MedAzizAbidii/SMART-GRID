import { useLocation } from "react-router-dom";
import { Construction } from "lucide-react";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";

const NEXT_ITERATION_NOTE =
  "This page is on the build roadmap for the next iteration, following the design system and page structure already established by Dashboard, Smart Grid, AI Detection, and Explainable AI.";

export default function ComingSoon({ title }) {
  const location = useLocation();
  return (
    <div>
      <div className="page-header">
        <div className="page-header-title">
          <h1 className="type-h2">{title || location.pathname}</h1>
        </div>
      </div>
      <Card>
        <EmptyState icon={Construction} title="Not yet built" description={NEXT_ITERATION_NOTE} />
      </Card>
    </div>
  );
}
