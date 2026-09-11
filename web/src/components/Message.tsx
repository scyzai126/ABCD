import "./Message.css";

/**
 * Empty and error states.
 *
 * An empty panel says what is missing and what would fill it -- absent metadata
 * is a fact about the pipeline, not a failure of the page.
 */
export function Message({
  title,
  children,
  tone = "neutral",
}: {
  title: string;
  children?: React.ReactNode;
  tone?: "neutral" | "problem";
}) {
  return (
    <div className={`message message--${tone}`}>
      <p className="message__title">{title}</p>
      {children && <div className="message__body">{children}</div>}
    </div>
  );
}
