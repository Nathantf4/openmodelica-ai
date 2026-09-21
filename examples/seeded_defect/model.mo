// EXPLICITLY SEEDED DEFECT: StepVoltag is not a library class.
model RLStep "Series MSL R-L circuit driven by a voltage step"
  parameter Modelica.Units.SI.Resistance R=2;
  parameter Modelica.Units.SI.Inductance L=0.5;
  parameter Modelica.Units.SI.Voltage V=10;
  parameter Modelica.Units.SI.Time ts=0.1;
  Modelica.Electrical.Analog.Sources.StepVoltag source(V=V, startTime=ts);
  Modelica.Electrical.Analog.Basic.Resistor resistor(R=R);
  Modelica.Electrical.Analog.Basic.Inductor inductor(L=L, i(start=0, fixed=true));
  Modelica.Electrical.Analog.Basic.Ground ground;
  Modelica.Units.SI.Current i;
  Real di(unit="A/s") "Explicit current derivative output";
equation
  connect(source.p, resistor.p);
  connect(resistor.n, inductor.p);
  connect(inductor.n, source.n);
  connect(source.n, ground.p);
  i = inductor.i;
  di = der(i);
  annotation(uses(Modelica(version="4.1.0")), experiment(StopTime=2, Tolerance=1e-8));
end RLStep;
