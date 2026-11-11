const AUTHOR = { name: "Benjamin Nweke", profile: "https://github.com/CryptoGuy1" };
const REPOSITORY = "https://github.com/CryptoGuy1/well-operations-agent-platform";

export function Author({ className }: { className?: string }) {
  return (
    <p className={className ? `author ${className}` : "author"}>
      Built by <a href={AUTHOR.profile}>{AUTHOR.name}</a> ·{" "}
      <a href={REPOSITORY}>Source on GitHub</a>
    </p>
  );
}
