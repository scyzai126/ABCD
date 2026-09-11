import { DashboardView } from "./DashboardView";

export function ProjectDashboard() {
  return (
    <DashboardView
      level="project"
      title="Overview"
      subtitle="Every study in the database, summarised together. Narrow the slice with the filters and each figure below recalculates against it."
    />
  );
}
