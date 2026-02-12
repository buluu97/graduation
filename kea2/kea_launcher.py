import sys
import argparse
import unittest
from typing import List
from enum import IntEnum


class ReturnCode(IntEnum):
    SUCCESS = 0
    TEST_FAILURE = 1
    ERROR = 2


def _set_runner_parser(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]"):
    parser = subparsers.add_parser("run", help="run kea2")
    parser.add_argument(
        "-s",
        "--serial",
        dest="serial",
        required=False,
        default=None,
        type=str,
        help="The serial of your device. Can be found with `adb devices`",
    )

    parser.add_argument(
        "-t",
        "--transport-id",
        dest="transport_id",
        required=False,
        default=None,
        type=str,
        help="transport-id of your device, can be found with `adb devices -l`",
    )

    parser.add_argument(
        "-p",
        "--packages",
        dest="package_names",
        nargs="+",
        type=str,
        required=True,
        help="Specify the target app package name(s) to test (e.g., com.example.app). *Supports multiple packages: `-p pkg1 pkg2 pkg3`*",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        dest="output_dir",
        type=str,
        required=False,
        default="output",
        help="The ouput directory for logs and results"
    )

    parser.add_argument(
        "--running-minutes",
        dest="running_minutes",
        type=int,
        required=False,
        default=10,
        help="The time (in minutes) to run Kea2",
    )

    parser.add_argument(
        "--max-step",
        dest="max_step",
        type=int,
        required=False,
        help="The maxium number of monkey events to send",
    )

    parser.add_argument(
        "--throttle",
        dest="throttle_ms",
        type=int,
        required=False,
        help="The delay time (in milliseconds) between two monkey events",
    )
    
    parser.add_argument(
        "--driver-name",
        dest="driver_name",
        type=str,
        required=False,
        default="d",
        help="The name of driver used in the kea2's scripts. If `--driver-name d` is specified, you should use `d` to interact with a device, e..g, `self.d(..).click()`. ",
    )

    # Deprecated argument placeholder: keep parsing to provide a clear error message.
    parser.add_argument(
        "--agent",
        dest="agent",
        type=str,
        required=False,
        default=None,
        help=argparse.SUPPRESS,
    )

    parser.add_argument(
        "--log-stamp",
        dest="log_stamp",
        type=str,
        required=False,
        help="the stamp for log file and result file. (e.g., if `--log-stamp 123` is specified, the log files will be named as `fastbot_123.log` and `result_123.json`.)",
    )
    
    parser.add_argument(
        "--profile-period",
        dest="profile_period",
        type=int,
        required=False,
        default=25,
        help="The period (in the numbers of monkey events) to profile coverage and collect UI screenshots. Specifically, the UI screenshots are stored on the SDcard of the mobile device, and thus you need to set an appropriate value according to the available device storage.",
    )

    
    parser.add_argument(
        "--take-screenshots",
        dest="take_screenshots",
        required=False,
        action="store_true",
        default=False,
        help="Take the UI screenshot at every Monkey event. The screenshots will be automatically pulled from the mobile device to your host machine periodically",
    )

    parser.add_argument(
        "--pre-failure-screenshots",
        dest="pre_failure_screenshots",
        type=int,
        required=False,
        default=0,
        help="Dump n screenshots before failure. 0 means take screenshots for every step.",
    )

    parser.add_argument(
        "--post-failure-screenshots",
        dest="post_failure_screenshots",
        type=int,
        required=False,
        default=0,
        help="Dump n screenshots after failure. Should be smaller than --pre-failure-screenshots.",
    )

    parser.add_argument(
        "--device-output-root",
        dest="device_output_root",
        type=str,
        required=False,
        default="/sdcard/.kea2",
        help="The root of device output dir. Kea2 will temporarily save the screenshots and result log into `<device-output-root>/output_*********/`. Make sure the root dir can be access.",
    )

    # FBM sync options
    parser.add_argument(
        "--merge-fbm",
        dest="merge_fbm",
        action="store_true",
        required=False,
        help="(Experimental) FBM merge at startup. When enabled, pull FBM(s) from the device at startup, merge them with local PC FBM data.",
    )


    parser.add_argument(
        "--act-whitelist-file",
        dest="act_whitelist_file",
        required=False,
        type=str,
        help="Activity WhiteList File. Only the activities listed in the file can be explored during testing.",
    )

    parser.add_argument(
        "--act-blacklist-file",
        dest="act_blacklist_file",
        required=False,
        type=str,
        help="Activity BlackList File. The activities listed in the file will be avoided during testing.",
    )

    parser.add_argument(
        "--restart-app-period",
        dest="restart_app_period",
        type=int,
        required=False,
        default=0,
        help="The period (in the numbers of monkey events) to restart the app under test. 0 means no restart.",
    )

    parser.add_argument(
        "extra",
        nargs=argparse.REMAINDER,
        help="Extra args (e.g. propertytest & --). See docs (https://github.com/ecnusse/Kea2/blob/main/docs/manual_en.md) for details.",
    )


def extra_args_info_logger(args):
    if args.unittest_args:
        print("Captured unittest args:", args.unittest_args, flush=True)
    if args.propertytest_args:
        print("Captured propertytest args:", args.propertytest_args, flush=True)
    if args.extra:
        print("Captured extra args (Will be appended to fastbot launcher):", args.extra, flush=True)


def driver_info_logger(args):
    print("[INFO] Driver Settings:", flush=True)

    for name, value in vars(args).items():
        if name in ["take_screenshots", "pre_failure_screenshots", "post_failure_screenshots",
                    "extra", "unittest_args", "propertytest_args", "subparser"]:
            continue
        if value:
            print(f"  {name}: {value}", flush=True)
    
    if args.take_screenshots:
        print("  take_screenshots:", args.take_screenshots, flush=True)
        if args.pre_failure_screenshots:
            print("  pre_failure_screenshots:", args.pre_failure_screenshots, flush=True)
        if args.post_failure_screenshots:
            print("  post_failure_screenshots:", args.post_failure_screenshots, flush=True)


def parse_args(argv: List):
    parser = argparse.ArgumentParser(description="Kea2")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _set_runner_parser(subparsers)
    args = parser.parse_args(argv)
    return args


def _sanitize_args(args):
    args.mode = None
    args.propertytest_args = None
    if args.agent is not None:
        raise ValueError("--agent is deprecated and native mode is no longer supported. Please remove this parameter.")
    if not args.driver_name:
        if args.extra == []:
            args.driver_name = "d"
        else:
            raise ValueError("--driver-name should be specified when customizing script")
    
    extra_args = {
        "unittest": [],
        "propertytest": [],
        "extra": []
    }    

    for i in range(len(args.extra)):
        if args.extra[i] == "unittest":
            current = "unittest"
        elif args.extra[i] == "propertytest":
            current = "propertytest"
        elif args.extra[i] == "--":
            current = "extra"
        else:
            extra_args[current].append(args.extra[i])
    setattr(args, "unittest_args", [])
    setattr(args, "propertytest_args", [])
    args.unittest_args = extra_args["unittest"]
    args.propertytest_args = extra_args["propertytest"]
    args.extra = extra_args["extra"]


def run(args=None) -> ReturnCode:
    if args is None:
        args = parse_args(sys.argv[1:])
    _sanitize_args(args)
    driver_info_logger(args)
    extra_args_info_logger(args)

    from kea2 import KeaTestRunner, HybridTestRunner, Options, keaTestLoader, KeaRuntimeError
    options = Options(
        driverName=args.driver_name,
        packageNames=args.package_names,
        serial=args.serial,
        transport_id=args.transport_id,
        running_mins=args.running_minutes,
        maxStep=args.max_step,
        throttle=args.throttle_ms,
        output_dir=args.output_dir,
        log_stamp=args.log_stamp,
        profile_period=args.profile_period,
        take_screenshots=args.take_screenshots,
        pre_failure_screenshots=args.pre_failure_screenshots,
        post_failure_screenshots=args.post_failure_screenshots,
        device_output_root=args.device_output_root,
        act_whitelist_file=args.act_whitelist_file,
        act_blacklist_file=args.act_blacklist_file,
        restart_app_period=args.restart_app_period,
        propertytest_args=args.propertytest_args,
        unittest_args=args.unittest_args,
        extra_args=args.extra,
        merge_fbm=args.merge_fbm,
    )


    is_hybrid_test = True if options.unittest_args else False
    if is_hybrid_test:
        HybridTestRunner.setOptions(options)
        testRunner = HybridTestRunner
        argv = ["python3 -m unittest"] + options.unittest_args
    if not is_hybrid_test:
        KeaTestRunner.setOptions(options)
        testRunner = KeaTestRunner
        argv = ["python3 -m unittest"] + options.propertytest_args

    try:
        program = unittest.main(
            module=None,
            argv=argv,
            testRunner=testRunner,
            testLoader=keaTestLoader,
            exit=False,
        )
    except KeaRuntimeError:
        return ReturnCode.ERROR
    except Exception:
        return ReturnCode.ERROR

    result = getattr(program, "result", None)
    if isinstance(result, int):
        return ReturnCode.TEST_FAILURE if result != 0 else ReturnCode.SUCCESS
    if result is None or not hasattr(result, "wasSuccessful"):
        return ReturnCode.ERROR
    return ReturnCode.SUCCESS if result.wasSuccessful() else ReturnCode.TEST_FAILURE
