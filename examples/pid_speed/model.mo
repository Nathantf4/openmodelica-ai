model SpeedPIDemo "Public MSL speed PI with torque saturation and viscous damping"
  parameter Modelica.Units.SI.Inertia J=0.2;
  parameter Modelica.Units.SI.RotationalDampingConstant d=0.1;
  parameter Modelica.Units.SI.AngularVelocity targetSpeed=10;
  parameter Modelica.Units.SI.Time stepTime=0.5;
  parameter Modelica.Units.SI.Torque torqueLimit=5;
  parameter Real k=0.6 "PI gain; deliberately poor baseline";
  parameter Modelica.Units.SI.Time Ti=0.08 "PI integral time";
  parameter Real Ni=0.9 "Anti-windup tracking time is Ni*Ti";
  Modelica.Blocks.Sources.Step reference(height=targetSpeed,startTime=stepTime)
    annotation(Placement(visible=true,transformation(origin={-120,30},extent={{-12,-12},{12,12}})));
  Modelica.Blocks.Continuous.LimPID controller(
    controllerType=Modelica.Blocks.Types.SimpleController.PI,
    k=k,Ti=Ti,Td=0,Ni=Ni,wp=1,yMax=torqueLimit,yMin=-torqueLimit,
    withFeedForward=false,initType=Modelica.Blocks.Types.Init.InitialState,
    xi_start=0,homotopyType=Modelica.Blocks.Types.LimiterHomotopy.NoHomotopy)
    annotation(Placement(visible=true,transformation(origin={-60,30},extent={{-16,-16},{16,16}})));
  Modelica.Mechanics.Rotational.Sources.Torque actuator(useSupport=false)
    annotation(Placement(visible=true,transformation(origin={5,30},extent={{-12,-12},{12,12}})));
  Modelica.Mechanics.Rotational.Components.Inertia inertia(J=J,
    phi(start=0,fixed=true),w(start=0,fixed=true))
    annotation(Placement(visible=true,transformation(origin={65,30},extent={{-16,-13},{16,13}})));
  Modelica.Mechanics.Rotational.Components.Damper damper(d=d,useHeatPort=false)
    annotation(Placement(visible=true,transformation(origin={130,30},extent={{-14,-14},{14,14}})));
  Modelica.Mechanics.Rotational.Components.Fixed housing
    annotation(Placement(visible=true,transformation(origin={175,30},extent={{-12,-12},{12,12}})));
  Modelica.Mechanics.Rotational.Sensors.SpeedSensor sensor
    annotation(Placement(visible=true,transformation(origin={65,-45},extent={{-14,-14},{14,14}})));
  Modelica.Units.SI.AngularVelocity setpoint,omega;
  Modelica.Units.SI.AngularAcceleration acceleration;
  Modelica.Units.SI.Torque tau;
  Real xi "PI integrator state for independent numerical verification";
  Real uRaw "Controller output before limiting";
equation
  assert(J>0 and d>=0 and k>0 and Ti>0 and Ni>0 and torqueLimit>0,"Positive plant/controller parameters required");
  connect(reference.y,controller.u_s) annotation(Line(points={{-106.8,30},{-79.2,30}},color={0,0,127}));
  connect(controller.y,actuator.tau) annotation(Line(points={{-42.4,30},{-9.4,30}},color={0,0,127}));
  connect(actuator.flange,inertia.flange_a) annotation(Line(points={{17,30},{49,30}},color={0,0,0}));
  connect(inertia.flange_b,damper.flange_a) annotation(Line(points={{81,30},{116,30}},color={0,0,0}));
  connect(damper.flange_b,housing.flange) annotation(Line(points={{144,30},{175,30}},color={0,0,0}));
  connect(inertia.flange_b,sensor.flange) annotation(Line(points={{81,30},{100,30},{100,-20},{51,-20},{51,-45}},color={0,0,0}));
  connect(sensor.w,controller.u_m) annotation(Line(points={{80.4,-45},{105,-45},{105,-80},{-60,-80},{-60,10.8}},color={0,0,127}));
  setpoint=reference.y;
  omega=sensor.w;
  acceleration=der(omega);
  tau=controller.y;
  xi=controller.I.y;
  uRaw=controller.limiter.u;
  annotation(uses(Modelica(version="4.1.0")),
    experiment(StartTime=0,StopTime=3,Interval=0.001,Tolerance=1e-8),
    Diagram(coordinateSystem(extent={{-155,-105},{200,105}}),graphics={
      Text(extent={{-150,98},{195,76}},textString="Astra + OpenModelica: speed PI, torque limited to +/-5 N.m",textColor={0,0,127}),
      Text(extent={{-145,-85},{190,-102}},textString="Public MSL toy plant — no employer data; compiler-checked, not engineering-certified",textColor={80,80,80})}));
end SpeedPIDemo;
