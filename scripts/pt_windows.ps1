param([Parameter(Mandatory=$true)][int]$ProcId)
# List every visible top-level window of a process (physical-pixel rects).
# Packet Tracer opens device/config dialogs as separate top-level windows, so
# MainWindowHandle alone is not enough — enumerate before capturing a dialog.
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class PTEnum {
    public delegate bool EnumProc(IntPtr hwnd, IntPtr lparam);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr lparam);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hwnd);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hwnd, StringBuilder sb, int max);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }

    public static void List(uint target) {
        SetProcessDPIAware();
        EnumWindows((hwnd, lp) => {
            uint pid; GetWindowThreadProcessId(hwnd, out pid);
            if (pid == target && IsWindowVisible(hwnd)) {
                StringBuilder sb = new StringBuilder(256);
                GetWindowText(hwnd, sb, 256);
                RECT r; GetWindowRect(hwnd, out r);
                Console.WriteLine("{0} [{1}] ({2},{3})-({4},{5})", hwnd, sb, r.Left, r.Top, r.Right, r.Bottom);
            }
            return true;
        }, IntPtr.Zero);
    }
}
"@
[PTEnum]::List([uint32]$ProcId)
