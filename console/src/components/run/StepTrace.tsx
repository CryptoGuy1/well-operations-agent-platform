import { useEffect, useId, useRef } from "react";

import type { Draft, Step } from "../../data/runTypes";
import { formatDuration, formatInteger, formatUsd } from "../../format";

const PLAY_INTERVAL_MS = 700;

export function StepTrace({
  steps,
  drafts,
  cursor,
  onCursor,
  playing,
  onPlaying,
}: {
  steps: Step[];
  drafts: Draft[];
  cursor: number;
  onCursor: (cursor: number) => void;
  playing: boolean;
  onPlaying: (playing: boolean) => void;
}) {
  const last = steps.length - 1;
  const id = useId();
  const current = useRef<HTMLLIElement>(null);

  // Playing advances one step at a time and stops at the last step.
  useEffect(() => {
    if (!playing) return;
    if (cursor >= last) {
      onPlaying(false);
      return;
    }
    const timer = window.setTimeout(() => {
      onCursor(cursor + 1);
    }, PLAY_INTERVAL_MS);
    return () => {
      window.clearTimeout(timer);
    };
  }, [playing, cursor, last, onCursor, onPlaying]);

  // Keep the current step in view after a replay action; never scroll the page on load.
  const follow = useRef(false);
  useEffect(() => {
    if (follow.current) current.current?.scrollIntoView({ block: "nearest" });
  }, [cursor]);

  if (steps.length === 0) {
    return <p className="note">This run recorded no steps.</p>;
  }

  const go = (n: number) => {
    follow.current = true;
    onPlaying(false);
    onCursor(Math.max(0, Math.min(last, n)));
  };

  return (
    <>
      <div className="replay" role="group" aria-label="Replay">
        <div className="replay__buttons">
          <button
            type="button"
            onClick={() => {
              go(0);
            }}
            disabled={cursor === 0}
          >
            First
          </button>
          <button
            type="button"
            onClick={() => {
              go(cursor - 1);
            }}
            disabled={cursor === 0}
          >
            Previous
          </button>
          <button
            type="button"
            aria-pressed={playing}
            onClick={() => {
              follow.current = true;
              if (!playing && cursor >= last) onCursor(0);
              onPlaying(!playing);
            }}
          >
            {playing ? "Pause" : "Play"}
          </button>
          <button
            type="button"
            onClick={() => {
              go(cursor + 1);
            }}
            disabled={cursor === last}
          >
            Next
          </button>
          <button
            type="button"
            onClick={() => {
              go(last);
            }}
            disabled={cursor === last}
          >
            Last
          </button>
        </div>
        <label htmlFor={`${id}-step`} className="replay__label">
          Step <span className="mono">{cursor + 1}</span> of{" "}
          <span className="mono">{steps.length}</span>
        </label>
        <input
          id={`${id}-step`}
          type="range"
          min={1}
          max={steps.length}
          value={cursor + 1}
          aria-valuetext={`Step ${cursor + 1} of ${steps.length}: ${stepTitle(steps[cursor], drafts)}`}
          onChange={(e) => {
            go(Number(e.target.value) - 1);
          }}
        />
      </div>
      <ol className="trace">
        {steps.map((step, i) => (
          <li
            key={step.seq}
            ref={i === cursor ? current : undefined}
            className={`trace__step trace__step--${step.type}${i > cursor ? " trace__step--later" : ""}`}
            aria-current={i === cursor ? "step" : undefined}
          >
            <button
              type="button"
              className="trace__select"
              onClick={() => {
                go(i);
              }}
              aria-label={`Go to step ${i + 1}: ${stepTitle(step, drafts)}`}
            >
              <span className="mono" aria-hidden="true">
                {i + 1}
              </span>
            </button>
            <div className="trace__body">
              <StepBody step={step} drafts={drafts} />
            </div>
          </li>
        ))}
      </ol>
    </>
  );
}

function draftNumber(step: Step, drafts: Draft[]): number {
  return drafts.filter((d) => d.seq <= step.seq).length;
}

function stepTitle(step: Step | undefined, drafts: Draft[]): string {
  if (!step) return "";
  switch (step.type) {
    case "model_call":
      return "Model call";
    case "tool_call":
      return `Tool call ${step.server}.${step.tool}`;
    case "draft":
      return draftNumber(step, drafts) === 1 ? "First draft submitted" : "Revised draft submitted";
    case "check":
      return "Checker run";
    case "approval":
      return "Approval recorded";
  }
}

function StepBody({ step, drafts }: { step: Step; drafts: Draft[] }) {
  switch (step.type) {
    case "model_call": {
      const cache = (step.cache_read_tokens ?? 0) + (step.cache_write_tokens ?? 0);
      return (
        <>
          <span className="trace__title">Model call</span>
          <span className="trace__meta mono">
            in {formatInteger(step.input_tokens ?? 0)}
            {cache > 0 && ` · cached ${formatInteger(cache)}`} · out{" "}
            {formatInteger(step.output_tokens ?? 0)}
          </span>
          <span className="trace__meta mono">
            {formatUsd(step.cost_usd)} · {formatDuration(step.latency_ms)}
            {step.stop_reason && ` · ${step.stop_reason}`}
          </span>
        </>
      );
    }
    case "tool_call":
      return (
        <>
          <span className="trace__title mono">{step.tool}</span>
          <span className="trace__meta mono">{step.server}</span>
          {Object.keys(step.arguments).length > 0 && (
            <dl className="trace__args mono">
              {Object.entries(step.arguments).map(([k, v]) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{typeof v === "string" ? v : JSON.stringify(v)}</dd>
                </div>
              ))}
            </dl>
          )}
          <span className="trace__meta mono">
            {step.is_error
              ? `error: ${step.error_code ?? "unknown"}`
              : `${formatInteger(step.returned ?? 0)} of ${formatInteger(step.matched ?? 0)} rows${step.capped ? " (capped)" : ""}`}{" "}
            · {formatDuration(step.latency_ms)}
          </span>
        </>
      );
    case "draft":
      return <span className="trace__title">{stepTitle(step, drafts)}</span>;
    case "check": {
      const draft = [...drafts].reverse().find((d) => d.seq < step.seq);
      const s = draft?.check?.summary;
      return (
        <>
          <span className="trace__title">Checker run</span>
          {s && (
            <span className="trace__meta mono">
              {formatInteger(s.verified ?? 0)} verified · {formatInteger(s.contradicted ?? 0)}{" "}
              contradicted · {formatInteger(s.unsupported ?? 0)} unsupported ·{" "}
              {formatInteger(s.unverifiable ?? 0)} unverifiable ·{" "}
              {formatInteger(s.unclaimed_number ?? 0)} unclaimed
            </span>
          )}
        </>
      );
    }
    case "approval":
      return <span className="trace__title">Approval recorded</span>;
  }
}
