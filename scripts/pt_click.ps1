param(
    [Parameter(Mandatory=$true)][int]$ProcId,
    [Parameter(Mandatory=$true)][int]$X,    # window-relative PHYSICAL pixels
    [Parameter(Mandatory=$true)][int]$Y,
    [switch]$Double,                        # double-click (opens device dialog in PT)
    [int]$DelayMs = 800
)
# Click inside the Packet Tracer window. Restores the window first (a minimized
# window reports rect at -32000). DPI-aware: X/Y are physical pixels, matching
# what pt_capture.ps1 produces. Remember: single click selects a device,
# DOUBLE click opens its configuration window.
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class PTClick {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hwnd, int cmd);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extra);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
[PTClick]::SetProcessDPIAware() | Out-Null
$p = Get-Process -Id $ProcId
$h = $p.MainWindowHandle
[PTClick]::ShowWindow($h, 9) | Out-Null      # SW_RESTORE
Start-Sleep -Milliseconds 600
[PTClick]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 400
$rect = New-Object PTClick+RECT
[PTClick]::GetWindowRect($h, [ref]$rect) | Out-Null
if ($rect.Left -le -30000) { throw "window is minimized" }
$ax = $rect.Left + $X; $ay = $rect.Top + $Y
[PTClick]::SetCursorPos($ax, $ay) | Out-Null
Start-Sleep -Milliseconds 200
foreach ($i in 1..$(if ($Double) { 2 } else { 1 })) {
    [PTClick]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)  # left down
    [PTClick]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)  # left up
    if ($i -eq 1 -and $Double) { Start-Sleep -Milliseconds 80 }
}
Start-Sleep -Milliseconds $DelayMs
Write-Output ("clicked pid=" + $ProcId + " window-rel ($X,$Y) -> screen ($ax,$ay) rect=(" + $rect.Left + "," + $rect.Top + ")")
