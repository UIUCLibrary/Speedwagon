$SOURCE_PATH        = "c:\source"
#$PYTHON             = $($(Get-Command python).source)
$WHEELS_PATH        = "c:\wheels"
$PYTHON_VENV        = "c:\standalone_venv"
$BUILD_PATH         = "c:\build\"
$OUTPUT_PATH        = "c:\dist"
Write-Host "Source:             $SOURCE_PATH"
Write-Host "Cache Path:         $WHEELS_PATH"
Write-Host "Build Path:         $BUILD_PATH"
Write-Host "Output Path:        $OUTPUT_PATH"

if (! (Test-Path $SOURCE_PATH)){
    throw "Invalid source path. Exepcting to locate source at $SOURCE_PATH"
}

$process = Start-Process -NoNewWindow -PassThru -Wait -FilePath cmake -ArgumentList "$SOURCE_PATH -G Ninja  -B $BUILD_PATH -DSPEEDWAGON_PYTHON_DEPENDENCY_CACHE=$WHEELS_PATH -DSPEEDWAGON_VENV_PATH=$PYTHON_VENV "
if (! $process.ExitCode -eq 0)
{
    throw "CMake failed to run configure. Exit code $($process.ExitCode)"
}

$process = Start-Process -NoNewWindow -PassThru -Wait -FilePath cmake -ArgumentList "--build $BUILD_PATH"
if (! $process.ExitCode -eq 0)
{
    throw "CMake failed to Build. Exit code $($process.ExitCode)"
}

$process = Start-Process -WorkingDirectory "$BUILD_PATH" -NoNewWindow -PassThru -Wait -FilePath ctest -ArgumentList "-T test -C Release"
if (! $process.ExitCode -eq 0)
{
    throw "CTest failed to Build. Exit code $($process.ExitCode)"
}

$CPACK_CONFIG = "$BUILD_PATH\CPackConfig.cmake"
Write-Host "Using $CPACK_CONFIG config to create standalone installers"
& cpack -C Release -G WIX`;NSIS`;ZIP --config $CPACK_CONFIG -B c:\dist -V
