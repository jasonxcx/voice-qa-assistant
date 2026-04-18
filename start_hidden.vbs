Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
WshShell.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
' 使用 python 运行，将输出重定向到日志文件
WshShell.Run "python app.py", 0, False