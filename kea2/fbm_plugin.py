import time
import random
import logging
import traceback
from pathlib import Path
from typing import Optional

from .adbUtils import ADBDevice

logger = logging.getLogger(__name__)


def _run_shell(cmd: str, device: Optional[str] = None, transport_id: Optional[str] = None) -> str:
    """Run a shell command on device using ADBDevice.shell and return stdout as string.
    """
    try:
        dev = ADBDevice()
        # AdbDevice.shell accepts a single string command
        return dev.shell(cmd)
    except Exception as e:
        logger.debug(f"ADB shell command failed: {cmd} ; err: {e}")
        raise


def create_device_snapshots(options) -> None:
    """Create on-device snapshot copies of fastbot fbm files for configured packages.

    Behavior:
    - Only runs when options.download_fbm is truthy.
    - Uses ADBDevice.shell (no subprocess) and retries cp up to max_retries.
    - Logs errors and never raises to avoid blocking startup.
    """
    # if not getattr(options, 'download_fbm', False):
    #     return

    pkgs = getattr(options, 'packageNames', []) or []
    for pkg in pkgs:
        src = f"/sdcard/fastbot_{pkg}.fbm"
        dst = f"/sdcard/fastbot_{pkg}.snapshot.fbm"

        try:
            # Check src existence
            check_cmd = f'test -f "{src}" && echo OK || echo NO'
            check_src = _run_shell(check_cmd, device=options.serial, transport_id=options.transport_id)
            if not (isinstance(check_src, str) and "OK" in check_src):
                print(f"Source FBM not found on device for package {pkg}: {src}. Skipping snapshot creation.", flush=True)
                continue
        except Exception as e:
            print(f"Failed to verify source FBM existence for {pkg}: {e}. Skipping.", flush=True)
            continue

        max_retries = 3
        success = False
        for attempt in range(1, max_retries + 1):
            try:
                print(f"Attempt {attempt}: creating device snapshot: cp {src} {dst}", flush=True)
                _run_shell(f'cp "{src}" "{dst}"', device=options.serial, transport_id=options.transport_id)

                # verify snapshot exists
                verify_cmd = f'test -f "{dst}" && echo OK || echo NO'
                verify = _run_shell(verify_cmd, device=options.serial, transport_id=options.transport_id)
                if isinstance(verify, str) and "OK" in verify:
                    print(f"Snapshot created on device for package {pkg}: {dst}", flush=True)
                    success = True
                    break
                else:
                    print(f"Snapshot verify failed on attempt {attempt} for {pkg}: {verify}", flush=True)
            except Exception as e:
                print(f"adb shell cp attempt {attempt} failed for {pkg}: {e}", flush=True)

            # backoff
            sleep_time = min(5.0, 0.5 * (2 ** (attempt - 1))) + random.uniform(0, 0.1)
            time.sleep(sleep_time)

        if not success:
            print(f"Giving up creating snapshot on device for {pkg} after {max_retries} attempts", flush=True)


def finalize_and_merge(options) -> None:
    """Pull device fbms, compute deltas and merge deltas into PC core fbm.

    Uses kea2.fbm_parser.FBMMerger.pull_and_merge_to_pc for each package.
    """
    try:
        from .fbm_parser import FBMMerger
    except Exception as e:
        logger.debug(f"FBM merger unavailable for finalize: {e}")
        return

    merger = FBMMerger()
    pkgs = getattr(options, 'packageNames', []) or []
    for pkg in pkgs:
        try:
            logger.info(f"Finalizing FBM delta for package: {pkg}")
            ok = merger.pull_and_merge_to_pc(pkg, device=options.serial, transport_id=options.transport_id)
            if ok:
                logger.info(f"Delta merge completed for package: {pkg}")
            else:
                logger.debug(f"Delta merge reported failure for package: {pkg}")
        except Exception as e:
            logger.debug(f"Error finalizing delta for {pkg}: {e}")


import functools

def fbm_run_hook(func):
    """Decorator to wrap KeaTestRunner.run: perform pre-run snapshot creation and post-run finalize/merge.

    The decorator uses `create_device_snapshots` before the run and `finalize_and_merge` after run
    (whether run raised or returned).
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Pre-run snapshot creation
        try:
            create_device_snapshots(getattr(self, 'options', None))
        except Exception as e:
            logger.debug(f"Pre-run FBM snapshot creation failed: {e}")
            traceback.print_exc()

        # Execute original run
        res = None
        try:
            res = func(self, *args, **kwargs)
            return res
        finally:
            # Post-run finalize/merge
            try:
                # allow self or options passed
                opts = getattr(self, 'options', None)
                if opts:
                    finalize_and_merge(opts)
            except Exception as e:
                logger.debug(f"Post-run FBM finalize failed: {e}")
                traceback.print_exc()

    return wrapper

