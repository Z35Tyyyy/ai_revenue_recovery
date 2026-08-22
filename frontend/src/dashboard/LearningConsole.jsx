import React from "react";
import { Card, Pill, Icon } from "../components/ui.jsx";
import { useMetrics } from "../lib/useData.js";
import { classLabel, actionLabel } from "../lib/labels.js";

const CLASS_ORDER = [
  "insufficient_funds", "soft_decline", "transient",
  "needs_card_update", "needs_reauth", "hard_decline",
];
const ACTION_ORDER = [
  "retry_optimal", "retry_now", "dunning_nudge",
  "request_card_update", "switch_method", "offer_grace",
];

export function LearningConsole() {
  const { metrics, loading } = useMetrics();
  const bandit = metrics?.holdout?.bandit || {};

  if (loading) return <div className="dash__loading mono">loading policy…</div>;

  const actions = ACTION_ORDER.filter((a) =>
    Object.values(bandit).some((row) => row[a] != null)
  );
  const classes = CLASS_ORDER.filter((c) => bandit[c]);
  const allRates = classes.flatMap((c) => Object.values(bandit[c]));
  const max = Math.max(...allRates, 0.01);

  const bestOf = (c) => {
    const e = Object.entries(bandit[c] || {}).sort((a, b) => b[1] - a[1])[0];
    return e ? e[0] : null;
  };

  return (
    <div className="page">
      <p className="page__lead">
        A contextual bandit (Thompson sampling over class × action) learns, from live outcomes,
        how well <em>each action</em> works for each failure class. Every cell is the bandit&rsquo;s
        current success estimate for that action; the engine exploits the top-scoring action (marked
        &#10003;) in each row. These are per-action estimates on the live stream — distinct from the
        whole-policy recovery rates on the Console &amp; Experiments.
      </p>

      <Card className="matrix">
        <div className="matrix__scroll">
          <table className="matrix__table">
            <thead>
              <tr>
                <th className="matrix__corner">Failure class</th>
                {actions.map((a) => (
                  <th key={a} className="matrix__ah">{actionLabel(a)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {classes.map((c) => {
                const best = bestOf(c);
                return (
                  <tr key={c}>
                    <th className="matrix__rh">{classLabel(c)}</th>
                    {actions.map((a) => {
                      const v = bandit[c]?.[a];
                      if (v == null) return <td key={a} className="matrix__cell matrix__cell--empty">·</td>;
                      const intensity = 0.12 + (v / max) * 0.8;
                      return (
                        <td
                          key={a}
                          className={`matrix__cell ${a === best ? "matrix__cell--best" : ""}`}
                          style={{ background: `rgba(79,224,160,${intensity.toFixed(2)})` }}
                        >
                          <span className="tnum">{(v * 100).toFixed(1)}</span>
                          {a === best && <Icon name="check" size={11} />}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="matrix__legend mono">
          <span>lower</span>
          <span className="matrix__scale" />
          <span>higher · bandit&rsquo;s learned success estimate per action</span>
        </div>
      </Card>

      <div className="learn-cards">
        {classes.map((c) => {
          const best = bestOf(c);
          const rate = bandit[c]?.[best];
          return (
            <Card key={c} className="learn-card" hover>
              <div className="learn-card__cls">{classLabel(c)}</div>
              <div className="learn-card__pick">
                <Icon name="arrow" size={14} /> {actionLabel(best)}
              </div>
              <div className="learn-card__rate tnum">
                {(rate * 100).toFixed(1)}% <span className="learn-card__unit">learned</span>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
