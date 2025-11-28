Set WshShell = CreateObject("WScript.Shell")

' Start Flask App
WshShell.Run """C:\Users\windows 10\Desktop\AI_support\start_flask.cmd""", 0, False

' Wait 2 seconds
WScript.Sleep 2000

' Start Cloudflared Tunnel
WshShell.Run """C:\Users\windows 10\Desktop\AI_support\start_cloudflared.cmd""", 0, False

Set WshShell = Nothing
