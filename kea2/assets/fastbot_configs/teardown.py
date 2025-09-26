from kea2.adbUtils import adb_shell
import time



def common_teardown(self):
    print("===================== common_teardown =========================")
    
    PACKAGE_NAME = "it.feio.android.omninotes.alpha"
    MAIN_ACTIVITY = "it.feio.android.omninotes.alpha/it.feio.android.omninotes.MainActivity"

    adb_shell(["am","force-stop",PACKAGE_NAME])
    time.sleep(2)
    adb_shell(["am","start",MAIN_ACTIVITY])