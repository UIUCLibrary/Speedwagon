Set WshShell = CreateObject("WScript.Shell")
Set myArgs = WScript.Arguments.Named

Sub Main()
    If myArgs.Exists("with_console") Then
        python_runtime = "python.exe"
    Else
        python_runtime = "pythonw.exe"
    End If
    currentdir=Left(WScript.ScriptFullName,InStrRev(WScript.ScriptFullName,"\"))
    WshShell.CurrentDirectory = currentdir + "\bin"
    WshShell.Run(python_runtime + " -m speedwagon")
End Sub

 call Main
