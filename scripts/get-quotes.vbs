' get-quotes.vbs
' Double-click this on your desktop: fetches quotes and shows them in a window.
' Runs PowerShell fully hidden (no console flash, no prompts).
' Edit the counts below if you want a different default batch size.
Count = 10
Langs = ""            ' e.g. "ja,zh" for translated Eastern aphorisms
NoOtherSources = False

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
ps1 = fso.GetParentFolderName(WScript.ScriptFullName) & "\show-quotes.ps1"

cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & ps1 & """"
if NoOtherSources Then cmd = cmd & " -NoOtherSources"
cmd = cmd & " -Count " & Count
if Langs <> "" Then cmd = cmd & " -Langs """ & Langs & """"

sh.Run cmd, 0, False