#!/usr/bin/env python3
from cereal import car
from selfdrive.car.chrysler.values import Ecu, ECU_FINGERPRINT, CAR, FINGERPRINTS
from selfdrive.car import STD_CARGO_KG, scale_rot_inertia, scale_tire_stiffness, is_ecu_disconnected, gen_empty_fingerprint
from selfdrive.car.interfaces import CarInterfaceBase
from common.dp_common import common_interface_atl, common_interface_get_params_lqr

class CarInterface(CarInterfaceBase):
  @staticmethod
  def compute_gb(accel, speed):
    return float(accel) / 3.0

  @staticmethod
  def get_params(candidate, fingerprint=None, has_relay=False, car_fw=None):
    if fingerprint is None:
      fingerprint = gen_empty_fingerprint()

    ret = CarInterfaceBase.get_std_params(candidate, fingerprint, has_relay)
    ret.carName = "chrysler"
    ret.safetyModel = car.CarParams.SafetyModel.chrysler
    ret.lateralTuning.init('pid')
    ret.lateralTuning.pid.newKfTuned = False

    # Chrysler port is a community feature, since we don't own one to test
    ret.communityFeature = True

    # Speed conversion:              20, 45 mph
    ret.wheelbase = 3.089  # in meters for Pacifica Hybrid 2017
    ret.steerRatio = 16.2  # Pacifica Hybrid 2017
    ret.mass = 1964. + STD_CARGO_KG  # kg curb weight Pacifica 2017
    ret.steerLimitTimer = 0.4
    ret.steerRateCost = 0.7 #0.7 works well
    ret.minSteerSpeed = 0 # TF DEVICE

    ### INDI TUNE ###

    # innerLoopGain is curvature gain.
    # outerLoopGain is lane centering gain.
    # timeConstant is smoothness.
    # actuatorEffectiveness is gain modulation based on accuracy of path.
    # steerActuatorDelay is how far its looking ahead.
    # steerRateCost is how eager the steering is to make sudden changes.

    ret.lateralTuning.init('indi')
    ret.lateralTuning.indi.innerLoopGainBP = [0, 20]
    ret.lateralTuning.indi.innerLoopGainV = [4.0, 10.5]
    ret.lateralTuning.indi.outerLoopGainBP = [0, 20]
    ret.lateralTuning.indi.outerLoopGainV = [7.0, 11.5]
    ret.lateralTuning.indi.timeConstantBP = [0, 20]
    ret.lateralTuning.indi.timeConstantV = [0.5, 1.8]
    ret.lateralTuning.indi.actuatorEffectivenessBP = [0, 20]
    ret.lateralTuning.indi.actuatorEffectivenessV = [70.0, 75.0]
    ret.steerActuatorDelay = 0.8

    ### OLD PID TUNE - WORKED ON 0.7.7 ###

    pidscale = 0.145
    ret.lateralTuning.pid.kpBP, ret.lateralTuning.pid.kiBP, ret.lateralTuning.pid.kfBP = [[9., 20.], [9., 20.], [0.]]
    ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV, ret.lateralTuning.pid.kfV = [[0.15 * pidscale,0.30 * pidscale], [0.03 * pidscale,0.05 * pidscale], [0.00006 * pidscale]] # full torque for 10 deg at 80mph means 0.00007818594
    ret.lateralTuning.pid.kdBP, ret.lateralTuning.pid.kdV = [[0.], [0.1]]
    ret.steerActuatorDelay = 0.02
    
    ### MY PID TUNE - WORKS GOOD BUT JERKY ###

    #ret.lateralTuning.pid.kpBP, ret.lateralTuning.pid.kiBP = [[9., 20.], [9., 20.]]
    #ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.0375, 0.075], [0.0075, 0.0125]]
    #ret.lateralTuning.pid.kf = 0.00006   # full torque for 10 deg at 80mph means 0.00007818594
    #ret.steerActuatorDelay = 0.1 # in seconds
    #ret.steerRateCost = 0.7 #0.7 works well

    ## ARNE STOCK TUNE ##

    #ret.lateralTuning.pid.kpBP, ret.lateralTuning.pid.kiBP, ret.lateralTuning.pid.kfBP = [[9., 20.], [9., 20.], [0.]]
    #ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV, ret.lateralTuning.pid.kfV = [[0.15,0.30], [0.03,0.05], [0.00006]] # full torque for 10 deg at 80mph means 0.00007818594
    #ret.lateralTuning.pid.kdBP, ret.lateralTuning.pid.kdV = [[0.], [0.]]
    #ret.lateralTuning.pid.kfV = [0.00006]   # full torque for 10 deg at 80mph means 0.00007818594
    #ret.steerActuatorDelay = 0.1
    #ret.steerRateCost = 0.7

    ### STOCK TUNE ###

    #ret.lateralTuning.pid.kpBP, ret.lateralTuning.pid.kiBP = [[9., 20.], [9., 20.]]
    #ret.lateralTuning.pid.kpV, ret.lateralTuning.pid.kiV = [[0.15, 0.30], [0.03, 0.05]]
    #ret.lateralTuning.pid.kf = 0.00006   # full torque for 10 deg at 80mph means 0.00007818594
    #ret.steerActuatorDelay = 0.1
    #ret.steerRateCost = 0.7

    ret.minSteerSpeed = 0.
   
    if candidate in (CAR.JEEP_CHEROKEE, CAR.JEEP_CHEROKEE_2019):
      ret.wheelbase = 2.91  # in meters
      ret.steerRatio = 12.7
      ret.steerActuatorDelay = 0.2  # in seconds

    # dp
    ret = common_interface_get_params_lqr(ret)

    ret.centerToFront = ret.wheelbase * 0.44

    ret.minSteerSpeed = 3.8  # m/s
    if candidate in (CAR.PACIFICA_2019_HYBRID, CAR.PACIFICA_2020, CAR.JEEP_CHEROKEE_2019):
      # TODO allow 2019 cars to steer down to 13 m/s if already engaged.
      ret.minSteerSpeed = 17.5  # m/s 17 on the way up, 13 on the way down once engaged.

    # starting with reasonable value for civic and scaling by mass and wheelbase
    ret.rotationalInertia = scale_rot_inertia(ret.mass, ret.wheelbase)

    # TODO: start from empirically derived lateral slip stiffness for the civic and scale by
    # mass and CG position, so all cars will have approximately similar dyn behaviors
    ret.tireStiffnessFront, ret.tireStiffnessRear = scale_tire_stiffness(ret.mass, ret.wheelbase, ret.centerToFront)

    ret.enableCamera = bool(is_ecu_disconnected(fingerprint[0], FINGERPRINTS, ECU_FINGERPRINT, candidate, Ecu.fwdCamera) or has_relay)
    print("ECU Camera Simulated: {0}".format(ret.enableCamera))

    return ret

  # returns a car.CarState
  def update(self, c, can_strings, dragonconf):
    # ******************* do can recv *******************
    self.cp.update_strings(can_strings)
    self.cp_cam.update_strings(can_strings)

    ret = self.CS.update(self.cp, self.cp_cam)
    # dp
    self.dragonconf = dragonconf
    ret.cruiseState.enabled = common_interface_atl(ret, dragonconf.dpAtl)
    ret.canValid = self.cp.can_valid and self.cp_cam.can_valid

    # speeds
    ret.steeringRateLimited = self.CC.steer_rate_limited if self.CC is not None else False

    # events
    events = self.create_common_events(ret, extra_gears=[car.CarState.GearShifter.low],
                                       gas_resume_speed=2.)

    if ret.vEgo < self.CP.minSteerSpeed:
      events.add(car.CarEvent.EventName.belowSteerSpeed)

    ret.events = events.to_msg()

    # copy back carState packet to CS
    self.CS.out = ret.as_reader()

    return self.CS.out

  # pass in a car.CarControl
  # to be called @ 100hz
  def apply(self, c):

    if (self.CS.frame == -1):
      return []  # if we haven't seen a frame 220, then do not update.

    can_sends = self.CC.update(c.enabled, self.CS, c.actuators, c.cruiseControl.cancel, c.hudControl.visualAlert, self.dragonconf)

    return can_sends
