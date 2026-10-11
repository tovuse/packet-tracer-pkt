param(
    [int]$ProcId = 0,                # target process id (PacketTracer.exe); 0 = all PT processes
    [string]$Out = "$env:TEMP\pt_window.png"
)
# Capture Packet Tracer window content WITHOUT stealing focus, via PrintWindow.
# DPI-aware on purpose: Packet Tracer (Qt6) renders in physical pixels, and a
# DPI-unaware PowerShell sees logical coordinates (150% scaling -> mismatch).
# Capture and click scripts must therefore share the same physical coordinate space.
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class PTWin {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdc, uint flags);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
[PTWin]::SetProcessDPIAware() | Out-Null

$procs = Get-Process PacketTracer -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 }
if ($ProcId -ne 0) { $procs = $procs | Where-Object { $_.Id -eq $ProcId } }
foreach ($p in $procs) {
    $h = $p.MainWindowHandle
    $rect = New-Object PTWin+RECT
    [PTWin]::GetWindowRect($h, [ref]$rect) | Out-Null
    $w = $rect.Right - $rect.Left; $ht = $rect.Bottom - $rect.Top
    if ($w -le 0 -or $ht -le 0 -or $rect.Left -le -30000) { Write-Output ("pid=" + $p.Id + " minimized/hidden, skipped"); continue }
    $bmp = New-Object System.Drawing.Bitmap $w, $ht
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    [PTWin]::PrintWindow($h, $hdc, 2) | Out-Null   # 2 = PW_RENDERFULLCONTENT
    $g.ReleaseHdc($hdc); $g.Dispose()
    $file = $Out -replace '\.png$', ("_{0}.png" -f $p.Id)
    $bmp.Save($file); $bmp.Dispose()
    Write-Output ("pid=" + $p.Id + " rect=(" + $rect.Left + "," + $rect.Top + ")-(" + $rect.Right + "," + $rect.Bottom + ") -> " + $file)
}
