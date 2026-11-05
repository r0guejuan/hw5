import { AGENTS, type AgentState } from "../activity";
import { HandsomeDan } from "./HandsomeDan";

export function AgentBoard({ states, cheering }: { states: Record<string, AgentState>; cheering: boolean }) {
  return (
    <section aria-labelledby="agents-heading">
      <h3 id="agents-heading">Agents</h3>
      <div className="agent-grid">
        {AGENTS.map((agent) => {
          const { state, latest } = states[agent.id];
          return (
            <article key={agent.id} className={`agent-card ${state.toLowerCase()} ${cheering ? "cheering" : ""}`}>
              {(state === "Working" || cheering) && <span className="boola">Boola boola!</span>}
              <HandsomeDan tie={agent.tie} label={`Handsome Dan with a ${agent.tieName} bow tie`} />
              <strong>{agent.name}</strong>
              <span className="agent-state">{state}</span>
              <p>{latest || agent.role}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
