export function ComingNext({ title, summary }: { title: string; summary: string }) {
  return (
    <>
      <h1>{title}</h1>
      <p className="coming-next">
        <span className="eyebrow">Coming next</span>
        {summary}
      </p>
    </>
  );
}
