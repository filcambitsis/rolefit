export function descriptionParagraphs(text: string): string[] {
  // Keep source line breaks, joining short fragments introduced by inline links.
  const paragraphs: string[] = [];
  for (const line of text
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)) {
    const previous = paragraphs.at(-1);
    if (
      previous &&
      !/[.!?:]$/.test(previous) &&
      (line.length < 50 || previous.length < 5)
    ) {
      paragraphs[paragraphs.length - 1] += ` ${line}`;
    } else {
      paragraphs.push(line);
    }
  }
  // Some feeds supply a single long block; break it at sentence boundaries.
  return paragraphs.flatMap((paragraph) => {
    if (paragraph.length < 700) return [paragraph];
    const sentences = paragraph.split(/(?<=[.!?])\s+(?=[A-Z])/);
    const chunks: string[] = [];
    for (let i = 0; i < sentences.length; i += 3) {
      chunks.push(sentences.slice(i, i + 3).join(" "));
    }
    return chunks;
  });
}

export function Score({
  score,
  large = false,
}: {
  score: number | null;
  large?: boolean;
}) {
  return (
    <div
      className={`score ${large ? "score-large" : ""}`}
      aria-label={
        score === null
          ? "Not enough requirements extracted"
          : `${score}% requirement coverage`
      }
    >
      <span>
        {score ?? "—"}
        <small>{score === null ? "N/A" : "%"}</small>
      </span>
    </div>
  );
}
export function CompanyMark({
  company,
  index = 0,
}: {
  company: string;
  index?: number;
}) {
  return (
    <div className={`company-mark mark-${index % 5}`} aria-hidden="true">
      {company.slice(0, 1)}
    </div>
  );
}
