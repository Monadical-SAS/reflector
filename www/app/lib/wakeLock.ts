// Not possible yet in firefox
// https://bugzilla.mozilla.org/show_bug.cgi?id=1589554

const canWakeLock = () => "wakeLock" in navigator;

let wakelock: WakeLockSentinel | undefined;
async function lockWakeState() {
  if (!canWakeLock()) return;
  try {
    wakelock = await navigator.wakeLock.request();
    wakelock.addEventListener("release", () => {
      console.log(
        "Screen Wake State Locked:",
        wakelock ? !wakelock?.released : false,
      );
    });
    console.log("Screen Wake State Locked:", !wakelock.released);
  } catch (e) {
    console.error("Failed to lock wake state with reason:", e.message);
  }
}

function releaseWakeState() {
  if (wakelock) wakelock.release();
  wakelock = undefined;
}

export { lockWakeState, releaseWakeState };
