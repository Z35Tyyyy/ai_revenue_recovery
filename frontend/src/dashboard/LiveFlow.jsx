import React from "react";

// Live recovery-flow graph: failure type → the agent's move → outcome.
// Nodes and edges GROW as each streamed payment flows through, so you watch the
// end-to-end process build up in real time. (A process/decision graph — the model
// itself is gradient-boosted trees + a bandit, not a neural net.)

const CLASS_ORDER = [
  "insufficient_funds", "soft_decline", "transient",
  "needs_card_update", "needs_reauth", "hard_decline",
];
const ACTION_ORDER = [
  "retry_now", "retry_optimal", "dunning_nudge",
  "request_card_update", "switch_method", "offer_grace", "give_up",
];
const CLASS_SHORT = {
  insufficient_funds: "No funds", soft_decline: "Soft decline", transient: "Glitch",
  needs_card_update: "Card update", needs_reauth: "Re-auth", hard_decline: "Dead card",
};
const ACTION_SHORT = {
  retry_now: "Retry now", retry_optimal: "Wait", dunning_nudge: "Remind",
  request_card_update: "Ask card", switch_method: "Switch", offer_grace: "Grace",
  give_up: "Stop",
};

const VB_W = 1000;
const VB_H = 380;
const TOP = 74;
const BOT = 348;
const X = { cls: 175, act: 500, out: 825 };

function layout(order, counts) {
  const seen = order.filter((k) => counts[k]);
  const m = seen.length;
  return seen.map((k, i) => ({
    key: k,
    y: m <= 1 ? (TOP + BOT) / 2 : TOP + ((BOT - TOP) * i) / (m - 1),
    count: counts[k],
  }));
}

function edgePath(x1, y1, x2, y2) {
  const cx = (x1 + x2) / 2;
  return `M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`;
}

export function LiveFlow({ flow }) {
  const { n = 0, cls = {}, act = {}, ca = {}, ao = {}, won = 0, lost = 0, active } = flow || {};

  const classNodes = layout(CLASS_ORDER, cls);
  const actionNodes = layout(ACTION_ORDER, act);
  const outcomeNodes = [
    { key: "won", label: "Recovered", count: won, y: 150 },
    { key: "lost", label: "Not recovered", count: lost, y: 272 },
  ].filter((o) => o.count > 0);

  const posOf = (nodes, x) =>
    Object.fromEntries(nodes.map((nd) => [nd.key, { x, y: nd.y, count: nd.count }]));
  const cP = posOf(classNodes, X.cls);
  const aP = posOf(actionNodes, X.act);
  const oP = Object.fromEntries(outcomeNodes.map((o) => [o.key, { x: X.out, y: o.y, count: o.count }]));

  const maxNode = Math.max(1, ...classNodes.map((d) => d.count), ...actionNodes.map((d) => d.count));
  const maxEdge = Math.max(1, ...Object.values(ca), ...Object.values(ao));
  const r = (c) => 7 + 21 * Math.sqrt(c / maxNode);
  const w = (c) => 1.2 + 9 * (c / maxEdge);

  const caEdges = Object.entries(ca)
    .map(([k, v]) => { const [c, a] = k.split(">"); return { c, a, v, key: k }; })
    .filter((e) => cP[e.c] && aP[e.a]);
  const aoEdges = Object.entries(ao)
    .map(([k, v]) => { const [a, o] = k.split(">"); return { a, o, v, key: k }; })
    .filter((e) => aP[e.a] && oP[e.o]);

  const caActive = active ? `${active.cls}>${active.act}` : null;
  const aoActive = active ? `${active.act}>${active.out}` : null;

  return (
    <div className="flow">
      <svg viewBox={`0 0 ${VB_W} ${VB_H}`} className="flow__svg" preserveAspectRatio="xMidYMid meet">
        <text x={X.cls} y={34} className="flow__hd">FAILURE TYPE</text>
        <text x={X.act} y={34} className="flow__hd">AGENT&rsquo;S MOVE</text>
        <text x={X.out} y={34} className="flow__hd">OUTCOME</text>

        {/* edges: class → action */}
        {caEdges.map((e) => (
          <path
            key={`ca-${e.key}`}
            d={edgePath(cP[e.c].x + r(cP[e.c].count), cP[e.c].y, aP[e.a].x - r(aP[e.a].count), aP[e.a].y)}
            className={`flow__edge ${e.key === caActive ? "is-active" : ""}`}
            style={{ strokeWidth: w(e.v) }}
          />
        ))}
        {/* edges: action → outcome (green when recovered) */}
        {aoEdges.map((e) => (
          <path
            key={`ao-${e.key}`}
            d={edgePath(aP[e.a].x + r(aP[e.a].count), aP[e.a].y, oP[e.o].x - r(oP[e.o].count), oP[e.o].y)}
            className={`flow__edge ${e.o === "won" ? "flow__edge--won" : ""} ${e.key === aoActive ? "is-active" : ""}`}
            style={{ strokeWidth: w(e.v) }}
          />
        ))}

        {/* nodes */}
        {classNodes.map((nd) => (
          <g key={`c-${nd.key}`} className={`flow__node ${active?.cls === nd.key ? "is-active" : ""}`}>
            <circle cx={X.cls} cy={nd.y} r={r(nd.count)} />
            <text x={X.cls} y={nd.y - r(nd.count) - 6} className="flow__label">{CLASS_SHORT[nd.key] || nd.key}</text>
            <text x={X.cls} y={nd.y + 4} className="flow__count">{nd.count}</text>
          </g>
        ))}
        {actionNodes.map((nd) => (
          <g key={`a-${nd.key}`} className={`flow__node ${active?.act === nd.key ? "is-active" : ""}`}>
            <circle cx={X.act} cy={nd.y} r={r(nd.count)} />
            <text x={X.act} y={nd.y - r(nd.count) - 6} className="flow__label">{ACTION_SHORT[nd.key] || nd.key}</text>
            <text x={X.act} y={nd.y + 4} className="flow__count">{nd.count}</text>
          </g>
        ))}
        {outcomeNodes.map((o) => (
          <g
            key={`o-${o.key}`}
            className={`flow__node flow__node--${o.key} ${active?.out === o.key ? "is-active" : ""}`}
          >
            <circle cx={X.out} cy={o.y} r={r(o.count)} />
            <text x={X.out} y={o.y - r(o.count) - 6} className="flow__label">{o.label}</text>
            <text x={X.out} y={o.y + 4} className="flow__count">{o.count}</text>
          </g>
        ))}

        {n === 0 && (
          <text x={VB_W / 2} y={VB_H / 2} className="flow__empty">the recovery flow builds as the stream runs…</text>
        )}
      </svg>
    </div>
  );
}
