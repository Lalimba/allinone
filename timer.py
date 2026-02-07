import time
import os
import platform

print("Timer started for 15 minutes...")
time.sleep(15 * 60)  # 15 minutes

# Play a beep depending on the OS
if platform.system() == "Windows":
    import winsound
    winsound.Beep(60000, 15000)  # frequency, duration
else:
    # For Linux/Mac, attempt terminal bell 5 times
    for _ in range(5):
        print("\a")
        time.sleep(0.5)

print("⏰ Time's up! Check your tea or food!")
