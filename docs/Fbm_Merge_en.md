# FBM Merge (Experimental Feature)

## Overview
FBM Merge (Model Aggregation) supports distributed testing environments (multi-device parallel testing). At the end of each round, Fastbot models are aggregated to accelerate training and enable model sharing.

## How to Enable
Simply add the `--merge-fbm` parameter when running kea2:
```bash
kea2 run -s "emulator-5554" -p it.feio.android.omninotes.alpha --running-minutes 10 --merge-fbm propertytest discover -p quicktest.py
```

## Purpose
- Designed for distributed kea2 runs (one PC with multiple mobile devices).
- Aggregates FBM data from multiple devices to compensate for insufficient activity coverage on a single device.
- The merged FBM file is automatically maintained on the PC.
- The merging process automatically slims down the FBM file, greatly reducing file size and improving performance.

## Implementation Details
1. **Automatic Pull and Merge:**
   - At the start of kea2 run, a copy of the FBM file is pulled from the mobile device as the "starting point" for this round.
   - After the run, both the newly generated FBM file and the starting point file are pulled back to the PC.
   - The PC calculates the delta between the two files, obtains the new FBM data for this round, and merges it into the core FBM file on the PC.
   - The merging process uses file locks to prevent concurrent read/write conflicts.
2. **File Permissions:**
   - On Linux/MacOS, merged files have 644 permissions.
   - On Windows, Administrators have full control, Everyone has read-only, and permission inheritance is disabled (to simulate 644 permissions).
3. **File Slimming:**
   - Duplicate entries are removed at both the data structure and index levels to achieve file slimming.
     - **Data Structure Deduplication:** For the same action, regardless of how many times it appears across devices or test runs, only one action record is kept, and accumulate the trigger counts of the same activity that belongs to this action, avoiding redundant entries.
     - **Index Deduplication:** When saving the FBM file, deduplication was performed on the indexes. For example, the same string `MainActivity` only creates an index once, thereby reducing the space occupied by the FBM file.
   - On average, file size can be reduced by 90%. For example, a 6MB FBM file can be slimmed down to just 226KB, with entry count reduced from 87,933 to 6,025.
   - Example: Two entries like "MainActivity 15" and "MainActivity 10" are merged into one entry "MainActivity 25".

## Usage Notes
- Users only need to add the `--merge-fbm` parameter when running kea2 run; the PC-side FBM file will be maintained automatically.
- **Note:** The PC-side FBM file is not automatically pushed to the device. If you want it to take effect on the device, you need to manually push it to the `/sdcard` directory.
- The merged FBM file is located in the `configs/merge_fbm/` directory.

### Example: Push to Device
```bash
adb -s <devicename> push $root_dir/configs/merge_fbm/fastbot_<package_name>.fbm /sdcard
```

## Typical Use Cases
1. **First-time Testing on a New Device:** Push the merged FBM file to benefit from models accumulated on older devices.
2. **Large-scale Device Testing:** After each test, push the merged file from the PC to all devices to improve coverage consistency across devices.

## Console Output Example

The following image shows a sample console output after a successful FBM Merge:

![FBM Merge Console Example](images/fbm_merge_example.png)
