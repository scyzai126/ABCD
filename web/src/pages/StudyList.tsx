import { Link } from "react-router-dom";
import { api } from "../api/client";
import { formatCount } from "../charts/palette";
import { Message } from "../components/Message";
import { useAsync } from "../state/useAsync";
import "./StudyList.css";

export function StudyList() {
  const studies = useAsync(() => api.studies(), []);

  if (studies.error) {
    return (
      <Message title="Could not load the study list" tone="problem">
        <p>{studies.error.message}</p>
      </Message>
    );
  }

  return (
    <div className="studies">
      <header>
        <h1 className="studies__title">Studies</h1>
        <p className="studies__subtitle">
          Each study holds its own subjects and samples. Open one for a dashboard
          scoped to it.
        </p>
      </header>

      <ul className="studies__list" role="list">
        {(studies.data ?? []).map((study) => (
          <li key={study.study_id}>
            <Link to={`/studies/${study.study_id}`} className="studies__row">
              <span className="studies__name">{study.study_name ?? `Study ${study.study_id}`}</span>
              <span className="studies__desc">
                {study.title ?? "No title recorded for this study."}
              </span>
              <span className="studies__count num">
                {formatCount(study.count_bcrs)}
                <span className="studies__unit">BCRs</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
