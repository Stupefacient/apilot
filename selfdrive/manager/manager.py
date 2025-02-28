#!/usr/bin/env python3
import datetime
import os
import signal
import subprocess
import sys
import traceback
from multiprocessing import Process
from typing import List, Tuple, Union

import cereal.messaging as messaging
import selfdrive.sentry as sentry
from common.basedir import BASEDIR
from common.params import Params, ParamKeyType
from common.text_window import TextWindow
from selfdrive.boardd.set_time import set_time
from system.hardware import HARDWARE, PC
from selfdrive.manager.helpers import unblock_stdout
from selfdrive.manager.process import ensure_running, launcher
from selfdrive.manager.process_config import managed_processes
from selfdrive.athena.registration import register, UNREGISTERED_DONGLE_ID
from system.swaglog import cloudlog, add_file_handler
from system.version import is_dirty, get_commit, get_version, get_origin, get_short_branch, \
                           get_normalized_origin, terms_version, training_version, \
                           is_tested_branch, is_release_branch



def manager_init() -> None:
  # update system time from panda
  set_time(cloudlog)

  # save boot log
  subprocess.call("./bootlog", cwd=os.path.join(BASEDIR, "system/loggerd"))

  params = Params()
  params.clear_all(ParamKeyType.CLEAR_ON_MANAGER_START)

  default_params: List[Tuple[str, Union[str, bytes]]] = [
    ("CompletedTrainingVersion", "0"),
    ("DisengageOnAccelerator", "0"),
    ("GsmMetered", "1"),
    ("HasAcceptedTerms", "0"),
    ("LanguageSetting", "main_en"),
    ("OpenpilotEnabledToggle", "1"),
    ("ShowDebugUI", "1"),
    ("ShowDateTime", "1"),
    ("ShowHudMode", "1"),
    ("ShowSteerRotate", "1"),
    ("ShowPathEnd", "1"),
    ("ShowAccelRpm", "1"),
    ("ShowTpms", "1"),
    ("ShowSteerMode", "1"),
    ("ShowDeviceState", "1"),
    ("ShowConnInfo", "1"),
    ("ShowLaneInfo", "2"),
    ("ShowBlindSpot", "1"),
    ("ShowGapInfo", "1"),
    ("ShowDmInfo", "0"),
    ("ShowRadarInfo", "0"),
    ("ShowZOffset", "122"),
    ("ShowPathMode", "0"),
    ("ShowPathColor", "0"),
    ("ShowPathModeCruiseOff", "0"),
    ("ShowPathColorCruiseOff", "0"),
    ("ShowPathModeLane", "0"),
    ("ShowPathColorLane", "0"),
    ("ShowPathWidth", "100"),
    ("ShowPlotMode", "0"),
    ("AutoResumeFromGas", "1"),
    ("AutoResumeFromGasSpeed", "30"),
    ("AutoResumeFromGasSpeedMode", "0"),    
    ("AutoCancelFromGasMode", "1"),    
    ("OpkrPrebuiltOn", "0"),
    ("AutoCurveSpeedCtrlUse", "1"),
    ("AutoCurveSpeedFactor", "100"),
    ("AutoTurnControl", "0"),
    ("AutoTurnSpeed", "40"),
    ("AutoTurnTimeMax", "200"),
    ("AutoLaneChangeSpeed", "30"),
    ("AutoNaviSpeedCtrl", "1"),
    ("AutoNaviSpeedCtrlStart", "22"),
    ("AutoNaviSpeedCtrlEnd", "6"),
    ("AutoRoadLimitCtrl", "0"),
    ("AutoResumeFromBrakeRelease", "1"),
    ("AutoResumeFromBrakeReleaseDist", "20"),
    ("AutoResumeFromBrakeReleaseLeadCar", "1"),
    ("AutoResumeFromBrakeCarSpeed", "40"),
    ("AutoResumeFromBrakeReleaseTrafficSign", "1"),
    ("XEgoObstacleCost", "6"),
    ("JEgoCost", "5"),
    ("AChangeCost", "180"),
    ("DangerZoneCost", "100"),
    ("LeadDangerFactor", "80"),
    ("LongControlActiveSound", "1"),
    ("AccelLimitEcoSpeed", "3"),
    ("StartAccelApply", "0"),
    ("StopAccelApply", "30"),
    ("TrafficStopDistanceAdjust", "400"),
    ("AutoSpeedUptoRoadSpeedLimit", "100"),
    ("ApplyLongDynamicCost", "0"), 
    ("AccelLimitConfusedModel", "1"),   
    ("AutoSpeedAdjustWithLeadCar", "0"),   
    ("TrafficStopAccel", "80"),     
    ("TrafficStopModelSpeed", "0"),         
    ("CruiseButtonMode", "0"),      
    ("GapButtonMode", "0"),      
    ("InitMyDrivingMode", "3"),      
    ("MySafeModeFactor", "80"),      
    ("LiveSteerRatioApply", "100"),      
    ("MyEcoModeFactor", "80"),  
    ("CruiseMaxVals1", "200"),
    ("CruiseMaxVals2", "140"),
    ("CruiseMaxVals3", "50"),
    ("CruiseMaxVals4", "20"),
    ("CruiseMaxVals5", "15"),
    ("CruiseMaxVals6", "15"),
    ("PrevCruiseGap", "4"),      
    ("CruiseSpeedMin", "10"),
    ("AutoSyncCruiseSpeedMax", "120"),       
    ("StopDistance", "600"), 
    ("CustomMapbox", "0"),    
    ("E2eDecelSpeed", "0"),        
    ("LongitudinalTuningKpV", "100"),     
    ("LongitudinalTuningKiV", "200"),     
    ("LongitudinalActuatorDelayUpperBound", "50"),     
    ("LongitudinalActuatorDelayLowerBound", "50"),     
    ("EnableRadarTracks", "0"),      
    ("EnableAutoEngage", "0"),      
    ("ApplyDynamicTFollow", "105"), 
    ("ApplyDynamicTFollowApart", "95"), 
    ("ApplyDynamicTFollowDecel", "105"), 
    ("SccConnectedBus2", "0"),   
    ("TFollowRatio", "100"),
    ("JerkUpperLowerLimit", "8"),    
    ("KeepEngage", "1"),
    ("UseLaneLineSpeed", "80"),    
    ("PathOffset", "0"),  
    ("PathCostApply", "100"),
    ("PathCostApplyLow", "100"),
    ("HapticFeedbackWhenSpeedCamera", "0"),       
    ("SoftHoldMode", "1"),       
    ("ApplyModelDistOrder", "28"),       
    ("SteeringRateCost", "700"),       
    ("LateralMotionCost", "11"),       
    ("LateralAccelCost", "0"),       
    ("LateralJerkCost", "5"),       
    ("SteerActuatorDelay", "30"),       
    ("CruiseControlMode", "4"),
    ("CruiseOnDist", "0"),
    ("SteerRatioApply", "0"),
    ("SteerDeltaUp", "3"),       
    ("SteerDeltaDown", "7"),       
  ]
  if not PC:
    default_params.append(("LastUpdateTime", datetime.datetime.utcnow().isoformat().encode('utf8')))

  if params.get_bool("RecordFrontLock"):
    params.put_bool("RecordFront", True)

  # set unset params
  for k, v in default_params:
    if params.get(k) is None:
      params.put(k, v)

  # is this dashcam?
  if os.getenv("PASSIVE") is not None:
    params.put_bool("Passive", bool(int(os.getenv("PASSIVE", "0"))))

  if params.get("Passive") is None:
    raise Exception("Passive must be set to continue")

  # Create folders needed for msgq
  try:
    os.mkdir("/dev/shm")
  except FileExistsError:
    pass
  except PermissionError:
    print("WARNING: failed to make /dev/shm")

  # set version params
  params.put("Version", get_version())
  params.put("TermsVersion", terms_version)
  params.put("TrainingVersion", training_version)
  params.put("GitCommit", get_commit(default=""))
  params.put("GitBranch", get_short_branch(default=""))
  params.put("GitRemote", get_origin(default=""))
  params.put_bool("IsTestedBranch", is_tested_branch())

  # set dongle id
  reg_res = register(show_spinner=True)
  if reg_res:
    dongle_id = reg_res
  else:
    serial = params.get("HardwareSerial")
    raise Exception(f"Registration failed for device {serial}")
  os.environ['DONGLE_ID'] = dongle_id  # Needed for swaglog

  if not is_dirty():
    os.environ['CLEAN'] = '1'

  # init logging
  sentry.init(sentry.SentryProject.SELFDRIVE)
  cloudlog.bind_global(dongle_id=dongle_id,
                       version=get_version(),
                       origin=get_normalized_origin(),
                       branch=get_short_branch(),
                       commit=get_commit(),
                       dirty=is_dirty(),
                       device=HARDWARE.get_device_type())
  if os.path.isfile('/data/tmux_error.log'):
    os.remove('/data/tmux_error.log')


def manager_prepare() -> None:
  for p in managed_processes.values():
    p.prepare()


def manager_cleanup() -> None:
  # send signals to kill all procs
  for p in managed_processes.values():
    p.stop(block=False)

  # ensure all are killed
  for p in managed_processes.values():
    p.stop(block=True)

  cloudlog.info("everything is dead")


def manager_thread() -> None:

  Process(name="road_speed_limiter", target=launcher, args=("selfdrive.road_speed_limiter", "road_speed_limiter")).start()
  cloudlog.bind(daemon="manager")
  cloudlog.info("manager start")
  cloudlog.info({"environ": os.environ})

  params = Params()

  ignore: List[str] = []
  if params.get("DongleId", encoding='utf8') in (None, UNREGISTERED_DONGLE_ID):
    ignore += ["manage_athenad", "uploader"]
  if os.getenv("NOBOARD") is not None:
    ignore.append("pandad")
  ignore += [x for x in os.getenv("BLOCK", "").split(",") if len(x) > 0]

  sm = messaging.SubMaster(['deviceState', 'carParams'], poll=['deviceState'])
  pm = messaging.PubMaster(['managerState'])

  ensure_running(managed_processes.values(), False, params=params, CP=sm['carParams'], not_run=ignore)

  print_timer = 0
  while True:
    sm.update()

    started = sm['deviceState'].started
    ensure_running(managed_processes.values(), started, params=params, CP=sm['carParams'], not_run=ignore)

    running = ' '.join("%s%s\u001b[0m" % ("\u001b[32m" if p.proc.is_alive() else "\u001b[31m", p.name)
                       for p in managed_processes.values() if p.proc)
    print_timer = (print_timer + 1)%10
    if print_timer == 0:
      print(running)
    cloudlog.debug(running)

    # send managerState
    msg = messaging.new_message('managerState')
    msg.managerState.processes = [p.get_process_state_msg() for p in managed_processes.values()]
    pm.send('managerState', msg)

    # Exit main loop when uninstall/shutdown/reboot is needed
    shutdown = False
    for param in ("DoUninstall", "DoShutdown", "DoReboot"):
      if params.get_bool(param):
        shutdown = True
        params.put("LastManagerExitReason", f"{param} {datetime.datetime.now()}")
        cloudlog.warning(f"Shutting down manager - {param} set")

    if shutdown:
      break


def main() -> None:
  preBuiltOn = Params().get_bool("OpkrPrebuiltOn")
  preBuiltFile = '/data/openpilot/prebuilt'
  if not os.path.isdir("/data/openpilot"):
      pass
  elif not os.path.isfile(preBuiltFile) and preBuiltOn:
    os.system("cd /data/openpilot; touch prebuilt")
  elif os.path.isfile(preBuiltFile) and not preBuiltOn:
    os.system("cd /data/openpilot; rm -f prebuilt")

  prepare_only = os.getenv("PREPAREONLY") is not None

  manager_init()

  # Start UI early so prepare can happen in the background
  if not prepare_only:
    managed_processes['ui'].start()

  manager_prepare()

  if prepare_only:
    return

  # SystemExit on sigterm
  signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(1))

  try:
    manager_thread()
  except Exception:
    traceback.print_exc()
    sentry.capture_exception()
  finally:
    manager_cleanup()

  params = Params()
  if params.get_bool("DoUninstall"):
    cloudlog.warning("uninstalling")
    HARDWARE.uninstall()
  elif params.get_bool("DoReboot"):
    cloudlog.warning("reboot")
    HARDWARE.reboot()
  elif params.get_bool("DoShutdown"):
    cloudlog.warning("shutdown")
    HARDWARE.shutdown()


if __name__ == "__main__":
  unblock_stdout()

  try:
    main()
  except Exception:
    add_file_handler(cloudlog)
    cloudlog.exception("Manager failed to start")

    try:
      managed_processes['ui'].stop()
    except Exception:
      pass

    # Show last 3 lines of traceback
    error = traceback.format_exc(-3)
    error = "Manager failed to start\n\n" + error
    with TextWindow(error) as t:
      t.wait_for_exit()

    raise

  # manual exit because we are forked
  sys.exit(0)
