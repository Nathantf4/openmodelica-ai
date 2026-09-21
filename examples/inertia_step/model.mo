model InertiaStep "Frictionless MSL rotational inertia and step torque"
  parameter Modelica.Units.SI.Inertia J=0.2;
  parameter Modelica.Units.SI.Torque tau=2;
  parameter Modelica.Units.SI.Time ts=0.1;
  Modelica.Blocks.Sources.Step step(height=tau, startTime=ts);
  Modelica.Mechanics.Rotational.Sources.Torque torque(useSupport=false);
  Modelica.Mechanics.Rotational.Components.Inertia inertia(J=J,
    phi(start=0, fixed=true), w(start=0, fixed=true));
  Modelica.Units.SI.AngularVelocity omega;
  Modelica.Units.SI.Angle angle;
equation
  connect(step.y, torque.tau);
  connect(torque.flange, inertia.flange_a);
  omega = inertia.w;
  angle = inertia.phi;
  annotation(uses(Modelica(version="4.1.0")), experiment(StopTime=1, Tolerance=1e-8));
end InertiaStep;
