# show-quotes.ps1
# Fetches quotes via WSL (uv runs inside Linux, where the repo + .venv live)
# and shows the result in a scrollable Windows Forms window.
# Launched hidden by get-quotes.vbs / get-quotes.bat so no console window appears.
param(
    [int]$Count = 10,
    [string]$Langs = "",
    [switch]$NoOtherSources
)

$ErrorActionPreference = 'Continue'

function Show-Text([string]$Body) {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $form = New-Object System.Windows.Forms.Form
    $form.Text = 'Intentional Passages'
    $form.Size = New-Object System.Drawing.Size(720, 620)
    $form.StartPosition = 'CenterScreen'
    $form.KeyPreview = $true

    $text = New-Object System.Windows.Forms.TextBox
    $text.Multiline = $true
    $text.ReadOnly = $true
    $text.ScrollBars = 'Vertical'
    $text.WordWrap = $true
    $text.Dock = 'Fill'
    $text.Font = New-Object System.Drawing.Font('Consolas', 12)
    $text.Text = $Body
    $form.Controls.Add($text)

    $close = New-Object System.Windows.Forms.Button
    $close.Text = 'Close'
    $close.Size = New-Object System.Drawing.Size(120, 32)
    $close.Dock = 'Bottom'
    $close.Add_Click({ $form.Close() })
    $form.Controls.Add($close)

    $form.AcceptButton = $close          # Enter closes
    $form.Add_KeyDown({ if ($_.KeyCode -eq 'Escape') { $form.Close() } })

    [void]$form.ShowDialog()
}

function Get-WslInfo {
    # Derive distro + Linux repo root from this script's UNC path by splitting.
    #   \\wsl.localhost\Ubuntu\home\gustav\projects\q-quotes-fetcher\scripts\show-quotes.ps1
    #   -> ['', '', 'wsl.localhost', 'Ubuntu', 'home', 'gustav', ...]
    $me = $MyInvocation.MyCommand.Path
    $parts = @($me -split '\\')
    if ($parts.Count -lt 5 -or $parts[2] -ne 'wsl.localhost') {
        return $null
    }
    $distro = $parts[3]
    $rel = $parts[4..($parts.Count - 1)] -join '/'   # home/.../scripts/show-quotes.ps1
    $scriptDir = $rel.Substring(0, $rel.LastIndexOf('/'))
    $root = $scriptDir.Substring(0, $scriptDir.LastIndexOf('/'))  # strip /scripts
    return @{ Distro = $distro; Root = '/' + $root }
}

try {
    $info = Get-WslInfo
    if (-not $info) {
        Show-Text (@(
            'Could not determine the WSL repo location from this script path:',
            "  $($MyInvocation.MyCommand.Path)",
            '',
            'Keep the scripts/ folder inside the repo on the WSL share so the',
            'double-click shortcut can find the Linux repo root.'
        ) -join "`r`n")
        exit 0
    }

    $flagStr = ''
    if ($Count -ne 10) { $flagStr += " --count $Count" }
    if ($Langs) { $flagStr += " --langs $Langs" }
    if ($NoOtherSources.IsPresent) { $flagStr += " --no-other-sources" }

    $cmd = "cd $($info.Root) && uv run get-passages $flagStr"
    $all = & wsl.exe -d $info.Distro -- bash -lc $cmd 2>&1
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        Show-Text (@(
            'The quote fetcher failed (exit code ' + $exitCode + ').',
            '',
            ($all -join "`r`n"),
            '',
            'Run the following inside WSL to see the real error:',
            "  cd $($info.Root)",
            '  uv sync && uv run get-passages'
        ) -join "`r`n")
        exit 0
    }

    # Drop uv's informational stderr lines before showing.
    $lines = @($all) | Where-Object {
        $_ -notmatch '^(Using CPython|Creating virtual environment|Installed|Prepared|Built|Resolved|Audited|Checked|error:)'
    }
    Show-Text ($lines -join "`r`n")
} catch {
    $log = Join-Path (Split-Path -Parent $PSScriptRoot) 'data\gui-error.log'
    try { $_.Exception.ToString() | Out-File -FilePath $log -Encoding utf8 } catch { }
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            "An error occurred:`n$($_.Exception.Message)`n`nDetails written to:`n$log",
            'q-quotes-fetcher')
    } catch { }
}