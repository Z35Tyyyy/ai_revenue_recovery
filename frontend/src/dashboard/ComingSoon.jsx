import React from "react";

export function ComingSoon({ title, desc }) {
  return (
    <div>
      <div className="page-h">
        <h1>{title}</h1>
      </div>
      <div className="soon">
        <div className="st">{title} — next in this build</div>
        <div className="sd">{desc}</div>
      </div>
    </div>
  );
}
