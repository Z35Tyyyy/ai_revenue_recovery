import React from "react";
import { Link } from "react-router-dom";
import { Reveal } from "../components/Reveal.jsx";

export function Gateway() {
  return (
    <section className="gateway">
      <div className="container">
        <Reveal><h2 className="h1">Now, operate the engine.</h2></Reveal>
        <Reveal delay={0.08}>
          <p className="gateway-sub lead">
            The story ends here. Step into the console — a calm, data-driven environment for
            running recoveries, inspecting the agent, and watching it learn.
          </p>
        </Reveal>
        <Reveal delay={0.14}>
          <Link to="/dashboard" className="btn btn-primary btn-lg">Enter the console →</Link>
        </Reveal>
      </div>
    </section>
  );
}
