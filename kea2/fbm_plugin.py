import time
import random
import logging
import functools
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .keaUtils import KeaTestRunner, Options


from .adbUtils import ADBDevice
from .utils import catchException


logger = logging.getLogger(__name__)


@catchException("Error creating device FBM snapshots")
def create_device_snapshots(options: "Options") -> None:
    """Create on-device snapshot copies of fastbot fbm files for configured packages.

    Behavior:
    - Only runs when options.download_fbm is truthy.
    - Uses ADBDevice.shell (no subprocess) and retries cp up to max_retries.
    - Logs errors and never raises to avoid blocking startup.
    """

    for pkg in options.packageNames:
        src = f"/sdcard/fastbot_{pkg}.fbm"
        dst = f"/sdcard/fastbot_{pkg}.snapshot.fbm"

        try:
            # Check src existence
            check_cmd = f'test -f "{src}" && echo OK || echo NO'
            check_src = ADBDevice().shell(check_cmd)
            if not (isinstance(check_src, str) and "OK" in check_src):
                print(f"Source FBM not found on device for package {pkg}: {src}. Skipping snapshot creation.", flush=True)
                continue
        except Exception as e:
            logger.error(f"Failed to verify source FBM existence for {pkg}: {e}. Skipping.")
            continue

        max_retries = 3
        success = False
        for attempt in range(1, max_retries + 1):
            print(f"Attempt {attempt}: creating device snapshot: cp {src} {dst}", flush=True)
            ADBDevice().shell(f'cp "{src}" "{dst}"')

            # verify snapshot exists
            verify_cmd = f'test -f "{dst}" && echo OK || echo NO'
            verify = ADBDevice().shell(verify_cmd)
            if isinstance(verify, str) and "OK" in verify:
                print(f"Snapshot created on device for package {pkg}: {dst}", flush=True)
                success = True
                break
            else:
                print(f"Snapshot verify failed on attempt {attempt} for {pkg}: {verify}", flush=True)

            # backoff
            sleep_time = min(5.0, 0.5 * (2 ** (attempt - 1))) + random.uniform(0, 0.1)
            time.sleep(sleep_time)

        if not success:
            print(f"Giving up creating snapshot on device for {pkg} after {max_retries} attempts", flush=True)


@catchException("Error finalizing and merging FBM deltas")
def finalize_and_merge(options: "Options"):
    """Pull device fbms, compute deltas and merge deltas into PC core fbm.

    Uses kea2.fbm_parser.FBMMerger.pull_and_merge_to_pc for each package.
    """
    from .fbm_parser import FBMMerger

    merger = FBMMerger()
    for pkg in options.packageNames:
        logger.info(f"Finalizing FBM delta for package: {pkg}")
        ok = merger.pull_and_merge_to_pc(pkg, device=options.serial, transport_id=options.transport_id)
        if ok:
            logger.info(f"Delta merge completed for package: {pkg}")
        else:
            logger.debug(f"Delta merge reported failure for package: {pkg}")


def merge_fbm(func):
    """Decorator for KeaTestRunner.run: 
    
    Function: Merge FBM in multi-device test run to accelerate fastbot model training.

    The decorator uses `create_device_snapshots` before the run and `finalize_and_merge` after run.
    """
    @functools.wraps(func)
    def wrapper(self: "KeaTestRunner", *args, **kwargs):
        # Pre-run snapshot creation
        if self.options.download_fbm:
            create_device_snapshots(self.options)

        try:
            return func(self, *args, **kwargs)
        finally:
            # Post-run finalize/merge
            if self.options.upload_fbm:
                finalize_and_merge(self.options)

    return wrapper
