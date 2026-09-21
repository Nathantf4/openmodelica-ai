model ThreePhaseLineLoad "Balanced grounded-star source, R-L line and R load"
  parameter Modelica.Units.SI.Voltage Vpeak=230*sqrt(2);
  parameter Modelica.Units.SI.Frequency f=50;
  parameter Modelica.Units.SI.Resistance Rline=1;
  parameter Modelica.Units.SI.Inductance Lline=0.01;
  parameter Modelica.Units.SI.Resistance Rload=9;
  Modelica.Electrical.Polyphase.Sources.SineVoltage source(m=3,
    V=fill(Vpeak,3), f=fill(f,3), phase={0,-2*Modelica.Constants.pi/3,-4*Modelica.Constants.pi/3});
  Modelica.Electrical.Polyphase.Basic.Resistor lineR(m=3, R=fill(Rline,3));
  Modelica.Electrical.Polyphase.Basic.Inductor lineL(m=3, L=fill(Lline,3),
    inductor(each i(start=0, fixed=true)));
  Modelica.Electrical.Polyphase.Basic.Resistor load(m=3, R=fill(Rload,3));
  Modelica.Electrical.Polyphase.Basic.Star sourceStar(m=3), loadStar(m=3);
  Modelica.Electrical.Analog.Basic.Ground ground;
  Modelica.Units.SI.Current i[3], kcl[3], sumI;
  Modelica.Units.SI.Voltage v[3];
equation
  connect(source.plug_p, lineR.plug_p);
  connect(lineR.plug_n, lineL.plug_p);
  connect(lineL.plug_n, load.plug_p);
  connect(source.plug_n, sourceStar.plug_p);
  connect(load.plug_n, loadStar.plug_p);
  connect(sourceStar.pin_n, ground.p);
  connect(loadStar.pin_n, ground.p);
  for k in 1:3 loop
    i[k] = lineL.inductor[k].i;
    v[k] = source.plug_p.pin[k].v;
    kcl[k] = lineL.plug_n.pin[k].i + load.plug_p.pin[k].i;
  end for;
  sumI = sum(i);
  annotation(uses(Modelica(version="4.1.0")), experiment(StopTime=0.12, Tolerance=1e-8));
end ThreePhaseLineLoad;
