import { AGENTS, type FeedItem } from "../activity";
import { HandsomeDan } from "./HandsomeDan";

export function ActivityFeed({ items }: { items: FeedItem[] }) {
  return (
    <section aria-labelledby="activity-heading">
      <h3 id="activity-heading">Activity</h3>
      {items.length === 0 ? (
        <p className="empty">Nothing yet. Start the agent team to see their work here.</p>
      ) : (
        <ol className="feed" aria-live="polite">
          {[...items].reverse().map((item) => {
            const agent = AGENTS.find((a) => a.name === item.actor);
            return (
              <li key={item.seq} className={item.tone}>
                <strong className="feed-actor">
                  {agent && <HandsomeDan tie={agent.tie} label="" size={26} />}
                  {item.actor}
                </strong>
                <span>{item.text}</span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
