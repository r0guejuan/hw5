import type { Oversight } from "../types";

function Meter({ label, value, limit }: { label: string; value: number; limit: number }) {
  const percent = Math.min(100, Math.round((value / limit) * 100));
  return (
    <div className={`meter ${percent >= 80 ? "high" : ""}`}>
      <div className="meter-top">
        <span>{label}</span>
        <span>
          {value.toLocaleString()} of {limit.toLocaleString()}
        </span>
      </div>
      <div className="meter-bar" role="progressbar" aria-label={label} aria-valuenow={value} aria-valuemin={0} aria-valuemax={limit}>
        <div style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

export function TokenMeter({ usage }: { usage: Oversight["usage"] }) {
  return (
    <section aria-labelledby="tokens-heading">
      <h3 id="tokens-heading">Token meter</h3>
      <Meter label="Tokens this run" value={usage.tokens} limit={usage.token_limit} />
      <Meter label="Requests this run" value={usage.requests} limit={usage.request_limit} />
      <Meter label="Tokens today" value={usage.tokens_today} limit={usage.daily_limit} />
    </section>
  );
}
