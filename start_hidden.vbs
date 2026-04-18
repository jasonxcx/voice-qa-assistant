' 隐藏窗口启动程序
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw.exe E:\workspace\Project\interviewHelper\app.py", 0, False