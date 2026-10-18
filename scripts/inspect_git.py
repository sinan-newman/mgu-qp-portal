import subprocess

ps_script = """
Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*git*' } | ForEach-Object {
    [PSCustomObject]@{
        Id = $_.ProcessId
        Name = $_.Name
        Cmd = $_.CommandLine
    }
} | Format-List
"""

res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
print(res.stdout)
