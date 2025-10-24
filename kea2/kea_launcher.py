import sys
import argparse
import unittest
from typing import List
import os



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
        help="The target package names com.example.app",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        dest="output_dir",
        type=str,
        required=False,
        default="output",
        help="The output dir for saving logs and results."
    )

    parser.add_argument(
        "--agent",
        dest="agent",
        type=str,
        default="u2",
        choices=["native", "u2"],
        help="Running native fastbot or u2-fastbot. (Only u2-fastbot support PBT)",
    )

    parser.add_argument(
        "--running-minutes",
        dest="running_minutes",
        type=int,
        required=False,
        default=10,
        help="Time to run fastbot",
    )

    parser.add_argument(
        "--max-step",
        dest="max_step",
        type=int,
        required=False,
        help="maxium monkey events count to send",
    )

    parser.add_argument(
        "--throttle",
        dest="throttle_ms",
        type=int,
        required=False,
        help="The pause between two monkey event.",
    )
    
    parser.add_argument(
        "--driver-name",
        dest="driver_name",
        type=str,
        required=False,
        help="The name of driver in script.",
    )

    parser.add_argument(
        "--log-stamp",
        dest="log_stamp",
        type=str,
        required=False,
        help="the stamp for log file and result file, default: current time stamp",
    )
    
    parser.add_argument(
        "--profile-period",
        dest="profile_period",
        type=int,
        required=False,
        default=25,
        help="Steps to profile the testing statistics.",
    )

    parser.add_argument(
        "--device-output-root",
        dest="device_output_root",
        type=str,
        required=False,
        default="/sdcard",
        help="The root of device output dir. (Saving tmp log files and screenshots)",
    )
    
    parser.add_argument(
        "--take-screenshots",
        dest="take_screenshots",
        required=False,
        action="store_true",
        default=False,
        help="Take screenshots for every step.",
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
        "--act-whitelist-file",
        dest="act_whitelist_file",
        required=False,
        type=str,
        help="Add Activity Whitelist File.",
    )

    parser.add_argument(
        "--act-blacklist-file",
        dest="act_blacklist_file",
        required=False,
        type=str,
        help="Add Activity Blacklist File.",
    )

    parser.add_argument(
        "extra",
        nargs=argparse.REMAINDER,
        help="Extra args (e.g. propertytest & --). See docs (https://github.com/ecnusse/Kea2/blob/main/docs/manual_en.md) for details.",
    )


def extra_args_info_logger(args):
    if args.agent == "native":
        print("[Warning] Property not availble in native agent.", flush=True)
    if args.unittest_args:
        print("Captured unittest args:", args.unittest_args, flush=True)
    if args.propertytest_args:
        print("Captured propertytest args:", args.propertytest_args, flush=True)
    if args.extra:
        print("Captured extra args (Will be appended to fastbot launcher):", args.extra, flush=True)


def driver_info_logger(args):
    print("[INFO] Driver Settings:", flush=True)
    if args.serial:
        print("  serial:", args.serial, flush=True)
    if args.transport_id:
        print("  transport_id:", args.transport_id, flush=True)
    if args.package_names:
        print("  package_names:", args.package_names, flush=True)
    if args.agent:
        print("  agent:", args.agent, flush=True)
    if args.running_minutes:
        print("  running_minutes:", args.running_minutes, flush=True)
    if args.throttle_ms:
        print("  throttle_ms:", args.throttle_ms, flush=True)
    if args.log_stamp:
        print("  log_stamp:", args.log_stamp, flush=True)
    if args.take_screenshots:
        print("  take_screenshots:", args.take_screenshots, flush=True)
        if args.pre_failure_screenshots:
            print("  pre_failure_screenshots:", args.pre_failure_screenshots, flush=True)
    if args.max_step:
        print("  max_step:", args.max_step, flush=True)


def parse_args(argv: List):
    parser = argparse.ArgumentParser(description="Kea2")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _set_runner_parser(subparsers)
    args = parser.parse_args(argv)
    return args


def _sanitize_args(args):
    args.mode = None
    args.propertytest_args = None
    if args.agent == "u2" and not args.driver_name:
        if args.extra == []:
            args.driver_name = "d"
        else:
            raise ValueError("--driver-name should be specified when customizing script in --agent u2")
    
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


def run(args=None):
    if args is None:
        args = parse_args(sys.argv[1:])
    _sanitize_args(args)
    driver_info_logger(args)
    extra_args_info_logger(args)

    from kea2 import KeaTestRunner, Options, HybridTestRunner
    from kea2.u2Driver import U2Driver
    options = Options(
        agent=args.agent,
        driverName=args.driver_name,
        Driver=U2Driver,
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
        device_output_root=args.device_output_root,
        act_whitelist_file=args.act_whitelist_file,
        act_blacklist_file=args.act_blacklist_file,
        propertytest_args=args.propertytest_args,
        unittest_args=args.unittest_args,
        extra_args=args.extra,
    )
    
    is_hybrid_test = True if options.unittest_args else False
    if is_hybrid_test:
        HybridTestRunner.setOptions(options)
        testRunner = HybridTestRunner
        argv = ["python3 -m unittest"] + options.unittest_args
    if not is_hybrid_test or options.agent == "u2":
        KeaTestRunner.setOptions(options)
        testRunner = KeaTestRunner
        argv = ["python3 -m unittest"] + options.propertytest_args
    unittest.main(module=None, argv=argv, testRunner=testRunner)
