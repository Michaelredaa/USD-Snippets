import json
import os
import sys
import re
import subprocess

from System.Collections.Specialized import StringCollection
from System.Text import Encoding
from System.IO import Path, File, StreamWriter
from Deadline.Scripting import ClientUtils, RepositoryUtils, FrameUtils, PathUtils, SystemUtils
from DeadlineUI.Controls.Scripting.DeadlineScriptDialog import DeadlineScriptDialog
from ThinkboxUI.Controls.Scripting import ComboControl, CheckBoxControl

########################################################################
## Globals
########################################################################
scriptDialog = None
dlSubmission = True
settings = []

########################################################################
## Main Function Called By Deadline
########################################################################
def __main__(*args):
    global scriptDialog
    global dlSubmission
    global settings

    scriptDialog = DeadlineScriptDialog()
    scriptDialog.SetTitle("Submit USD Job To Deadline")
    scriptDialog.SetIcon(scriptDialog.GetIcon('USD'))

    scriptDialog.AddTabControl("Tabs", 0, 0)

    # Tab 1
    # Description
    scriptDialog.AddTabPage("Job Options")
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid("Separator1","SeparatorControl","Job Description", 0, 0, colSpan=2)

    scriptDialog.AddControlToGrid("NameLabel","LabelControl","Job Name", 1, 0,"The name of your job. This is optional, and if left blank, it will default to 'Untitled'.", False)
    scriptDialog.AddControlToGrid("NameBox","TextControl","Untitled", 1, 1)
    settings.append("NameBox")

    scriptDialog.AddControlToGrid("CommentLabel","LabelControl","Comment", 2, 0,"A simple description of your job. This is optional and can be left blank.", False)
    scriptDialog.AddControlToGrid("CommentBox","TextControl","", 2, 1)

    scriptDialog.AddControlToGrid("DepartmentLabel","LabelControl","Department", 3, 0,"The department you belong to. This is optional and can be left blank.", False)
    scriptDialog.AddControlToGrid("DepartmentBox","TextControl","", 3, 1)
    settings.append("DepartmentBox")

    scriptDialog.AddControlToGrid("BatchNameLabel","LabelControl","Batch Name", 4, 0,"The batch name to group set of jobs. This is optional and can be left blank.", False)
    scriptDialog.AddControlToGrid("BatchNameBox","TextControl","", 4, 1)
    scriptDialog.EndGrid()

    # Job Options
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid("Separator2","SeparatorControl","Job Options", 0, 0, colSpan=3)

    scriptDialog.AddControlToGrid("PoolLabel","LabelControl","Pool", 1, 0,"The pool that your job will be submitted to.", False)
    scriptDialog.AddControlToGrid("PoolBox","PoolComboControl","none", 1, 1)
    settings.append("PoolBox")

    scriptDialog.AddControlToGrid("SecondaryPoolLabel","LabelControl","Secondary Pool", 2, 0,"The secondary pool lets you specify a Pool to use if the primary Pool does not have any available Workers.", False)
    scriptDialog.AddControlToGrid("SecondaryPoolBox","SecondaryPoolComboControl","", 2, 1)
    settings.append("SecondaryPoolBox")

    scriptDialog.AddControlToGrid("GroupLabel","LabelControl","Group", 3, 0,"The group that your job will be submitted to.", False)
    scriptDialog.AddControlToGrid("GroupBox","GroupComboControl","none", 3, 1)
    settings.append("GroupBox")

    scriptDialog.AddControlToGrid("PriorityLabel","LabelControl","Priority", 4, 0,"A job can have a numeric priority ranging from 0 to 100, where 0 is the lowest priority and 100 is the highest priority.", False)
    scriptDialog.AddRangeControlToGrid("PriorityBox","RangeControl", RepositoryUtils.GetMaximumPriority() / 2, 0, RepositoryUtils.GetMaximumPriority(), 0, 1, 4, 1)
    settings.append("PriorityBox")

    scriptDialog.AddControlToGrid("TaskTimeoutLabel","LabelControl","Task Timeout", 5, 0,"The number of minutes a Worker has to render a task for this job before it requeues it. Specify 0 for no limit.", False)
    scriptDialog.AddRangeControlToGrid("TaskTimeoutBox","RangeControl", 0, 0, 1000000, 0, 1, 5, 1)
    scriptDialog.AddSelectionControlToGrid("AutoTimeoutBox","CheckBoxControl", False,"Enable Auto Task Timeout", 5, 2,"If the Auto Task Timeout is properly configured in the Repository Options, then enabling this will allow a task timeout to be automatically calculated based on the render times of previous frames for the job.")

    scriptDialog.AddControlToGrid("ConcurrentTasksLabel","LabelControl","Concurrent Tasks", 6, 0,"The number of tasks that can render concurrently on a single Worker. This is useful if the rendering application only uses one thread to render and your Workers have multiple CPUs.", False)
    scriptDialog.AddRangeControlToGrid("ConcurrentTasksBox","RangeControl", 1, 1, 16, 0, 1, 6, 1)
    scriptDialog.AddSelectionControlToGrid("LimitConcurrentTasksBox","CheckBoxControl", True,"Limit Tasks To Worker's Task Limit", 6, 2,"If you limit the tasks to a Worker's task limit, then by default, the Worker won't dequeue more tasks then it has CPUs. This task limit can be overridden for individual Workers by an administrator.")

    scriptDialog.AddControlToGrid("MachineLimitLabel","LabelControl","Machine Limit", 7, 0,"Use the Machine Limit to specify the maximum number of machines that can render your job at one time. Specify 0 for no limit.", False)
    scriptDialog.AddRangeControlToGrid("MachineLimitBox","RangeControl", 0, 0, 1000000, 0, 1, 7, 1)
    scriptDialog.AddSelectionControlToGrid("IsBlacklistBox","CheckBoxControl", False,"Machine List Is A Deny List", 7, 2,"You can force the job to render on specific machines by using an allow list, or you can avoid specific machines by using a deny list.")
    settings.append("IsBlacklistBox")

    scriptDialog.AddControlToGrid("MachineListLabel","LabelControl","Machine List", 8, 0,"The list of machines on the deny list or allow list.", False)
    scriptDialog.AddControlToGrid("MachineListBox","MachineListControl","", 8, 1, colSpan=2)
    settings.append("MachineListBox")

    scriptDialog.AddControlToGrid("LimitGroupLabel","LabelControl","Limits", 9, 0,"The Limits that your job requires.", False)
    scriptDialog.AddControlToGrid("LimitGroupBox","LimitGroupControl","", 9, 1, colSpan=2)
    settings.append("LimitGroupBox")

    scriptDialog.AddControlToGrid("DependencyLabel","LabelControl","Dependencies", 10, 0,"Specify existing jobs that this job will be dependent on. This job will not start until the specified dependencies finish rendering.", False)
    scriptDialog.AddControlToGrid("DependencyBox","DependencyControl","", 10, 1, colSpan=2)

    scriptDialog.AddControlToGrid("OnJobCompleteLabel","LabelControl","On Job Complete", 11, 0,"If desired, you can automatically archive or delete the job when it completes.", False)
    scriptDialog.AddControlToGrid("OnJobCompleteBox","OnJobCompleteControl","Nothing", 11, 1)
    scriptDialog.AddSelectionControlToGrid("SubmitSuspendedBox","CheckBoxControl", False,"Submit Job As Suspended", 11, 2,"If enabled, the job will submit in the suspended state. This is useful if you don't want the job to start rendering right away. Just resume it from the Monitor when you want it to render.")
    scriptDialog.EndGrid()

    # USD
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid("Separator3","SeparatorControl","USD Options", 0, 0, colSpan=5)

    scriptDialog.AddControlToGrid("USDLabel","LabelControl","USD File", 1, 0,"The USD stage file to render.", False)
    scriptDialog.AddSelectionControlToGrid("usdFileBox","FileBrowserControl","","USD Files (*.usd *.usda *.usdc);;All Files (*)", 1, 1, colSpan=4)
    usdButton = scriptDialog.AddControlToGrid("UsdButton", "ButtonControl", "", 0, 4, "Open usdview")
    usdButton.setIcon(scriptDialog.windowIcon())
    usdButton.setFlat(True)
    usdButton.ValueModified.connect(OpenUsdview)
    settings.append("usdFileBox")

    scriptDialog.AddControlToGrid("OutputLabel","LabelControl","Output Render", 3, 0,"The path that the render will be. use `$F`, `<F>`, or `%04d`", False)
    scriptDialog.AddSelectionControlToGrid("OutputFileBox","FileBrowserControl","","", 3, 1, colSpan=4)
    settings.append("OutputFileBox")

    scriptDialog.AddControlToGrid("RenderSettingLabel","LabelControl","Render Setting", 4, 0,"The prim path of render setting to render with.\nIf empty it will take the default `/Render/rendersettings`", False)
    scriptDialog.AddControlToGrid("RenderSettingBox","TextControl","", 4, 1, colSpan=4)
    settings.append("RenderSettingBox")

    scriptDialog.AddControlToGrid("FramesLabel","LabelControl","Frame List", 5, 0,"The list of frames to render.", False)
    scriptDialog.AddControlToGrid("FramesBox","TextControl","", 5, 1, colSpan=4)
    settings.append("FramesBox")

    scriptDialog.AddControlToGrid("ChunkSizeLabel","LabelControl","Frames Per Task", 6, 0,"This is the number of frames that will be rendered at a time for each job task.", False)
    scriptDialog.AddRangeControlToGrid("ChunkSizeBox","RangeControl", 1, 1, 1000000, 0, 1, 6, 1)
    settings.append("ChunkSizeBox")

    scriptDialog.AddSelectionControlToGrid("SubmitUSDFileBox","CheckBoxControl", False, "Submit USD files", 6, 2,"If this option is enabled, the USD files will be submitted with the job, and then copied locally to the Worker machine during rendering.")
    settings.append("SubmitUSDFileBox")

    verbose = [str(x) for x in range(10)]
    scriptDialog.AddControlToGrid("verboseLabel","LabelControl","Verbose Level", 7, 0,"The verbosity level", False)
    scriptDialog.AddComboControlToGrid("VerboseBox","ComboControl", verbose[0], verbose, 7, 1)
    settings.append("VerboseBox")

    scriptDialog.AddControlToGrid("ThreadsLabel","LabelControl","Threads", 7, 2,"The number of rendering threads (0 to use the value specified in the Clarisse configuration file).", False)
    scriptDialog.AddRangeControlToGrid("ThreadsBox","RangeControl", 0, 0, 256, 0, 1, 7, 3)
    settings.append("ThreadsBox")

    executables = GetExecutables()
    scriptDialog.AddControlToGrid("ExecutableLabel","LabelControl","Executable", 8, 0,"The excutable to Render using.", False)
    ExecutableBox = scriptDialog.AddComboControlToGrid("ExecutableBox","ComboControl", executables[0], executables, 8, 1)
    settings.append("ExecutableBox")

    versions = GetExecutableVersions(ExecutableBox.currentText())
    scriptDialog.AddControlToGrid("VersionLabel","LabelControl","Version", 8, 2,"The version of USD render to render with.", False)
    versionBox = scriptDialog.AddComboControlToGrid("VersionBox","ComboControl", versions[-1], versions, 8, 3)
    settings.append("VersionBox")

    scriptDialog.AddControlToGrid("RendererLabel","LabelControl","Renderer", 10, 0,"The renderer to Render with.", False)

    renderers = ("Karma CPU","Karma XPU")
    RendererBox = scriptDialog.AddComboControlToGrid("RendererBox","ComboControl", renderers[-1], renderers, 10, 1)
    settings.append("RendererBox")

    # Tab 2
    scriptDialog.EndGrid()
    scriptDialog.EndTabPage()

    # tiling
    scriptDialog.AddTabPage("Advanced Options")
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid("Separator1","SeparatorControl","Titling", 0, 0, colSpan=4)
    TileCB = scriptDialog.AddSelectionControlToGrid("TileCB","CheckBoxControl", False,"Number of tiles", 1, 0,"Enable render tiling.", colSpan=1)
    scriptDialog.AddRangeControlToGrid("XTileRange","RangeControl", 1, 0, 1000000, 0, 0, 1, 1, colSpan=1)
    scriptDialog.AddRangeControlToGrid("YTileRange","RangeControl", 1, 0, 1000000, 0, 0, 1, 2, colSpan=1)
    scriptDialog.AddSelectionControlToGrid("DeleteTilesCB","CheckBoxControl", False,"Delete tiles after combine", 2, 0,"Delete tiles images after combine.", colSpan=1)
    settings.extend(["XTileRange","YTileRange","DeleteTilesCB"])
    scriptDialog.EndGrid()

    OnTileCBChanged(False)

    # render overrides
    # res
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid("Separator2","SeparatorControl","Render Overrides", 0, 0, colSpan=4)
    OverrideSizeCB = scriptDialog.AddSelectionControlToGrid("OverrideSizeCB","CheckBoxControl", False,"Override Resolution", 1, 0,"Enable this option to override the Width and Height (respectively) of the rendered images.", colSpan=1)
    scriptDialog.AddRangeControlToGrid("WidthSizeRange","RangeControl", 1920, 0, 1000000, 0, 0, 1, 1)
    scriptDialog.AddRangeControlToGrid("HeightSizeRange","RangeControl", 1080, 0, 1000000, 0, 0, 1, 2)

    scriptDialog.AddControlToGrid("ScaleSizeLabel","LabelControl","Resoluation Scale", 2, 0,"Scale teh output image by teh given percentage", False)
    scriptDialog.AddRangeControlToGrid("ScaleSizeRange","RangeControl", 100, 0, 1000000, 0, 0, 2, 1)
    settings.extend(["WidthSizeRange","HeightSizeRange","ScaleSizeRange"])
    OnOverrideSizeChanged(False)

    # camera
    overrideCameraCB = scriptDialog.AddSelectionControlToGrid("overrideCameraCB","CheckBoxControl", False,"Override Camera", 3, 0,"Enable this option to override the camera of the render settings.", colSpan=1)
    scriptDialog.AddControlToGrid("CameraBox","TextControl","/cameras/camera1", 3, 1, colSpan=4)
    settings.append("CameraBox")
    scriptDialog.EndGrid()
    OnOverrideCameraChanged(False)

    scriptDialog.EndTabPage()
    scriptDialog.EndTabControl()

    # Submit
    scriptDialog.AddGrid()

    scriptDialog.AddHorizontalSpacerToGrid("HSpacer1", 0, 0)
    submitButton = scriptDialog.AddControlToGrid("SubmitButton","ButtonControl","Submit", 0, 3, expand=False)
    submitButton.ValueModified.connect(SubmitButtonPressed)

    closeButton = scriptDialog.AddControlToGrid("CloseButton","ButtonControl","Close", 0, 4, expand=False)
    closeButton.ValueModified.connect(scriptDialog.closeEvent)
    scriptDialog.EndGrid()

    scriptDialog.LoadSettings(GetSettingsFilename(), settings)
    scriptDialog.EnabledStickySaving(settings, GetSettingsFilename())

    Callbacks()

    dlSubmission = True
    if len(args) > 0:
        dlSubmission = False
        data = json.loads(args[0])

        for key, value in data.items():
            scriptDialog.SetValue(key, value)

        SubmitButtonPressed()
        return

    scriptDialog.MakeTopMost()
    scriptDialog.ShowDialog(dlSubmission)



def CheckSubmissionParams():
    global scriptDialog
    global dlSubmission

    errors = []

    # Check if a valid frame range has been specified.
    frames = scriptDialog.GetValue("FramesBox")
    if(not FrameUtils.FrameRangeValid(frames)):
        errors.append("Frame range `{}` is not valid".format(frames))

    # Check if USD files exist.
    usdFile = scriptDialog.GetValue("usdFileBox")
    outputPath = scriptDialog.GetValue("OutputFileBox")

    USDExtension = usdFile.rsplit('.', 1)[-1]
    if(not File.Exists(usdFile)):
        errors.append("The USD file `{}` does not exist".format(usdFile))

    if USDExtension.lower() not in ('usd', 'usda', 'usdc'):
        errors.append("The USD file `{}` have incorrect file extension `{}`".format(usdFile, USDExtension))

    if not outputPath:
        errors.append("Cannot leave the output path empty")

    if len(errors) > 0 and dlSubmission:
        scriptDialog.ShowMessageBox("Could not submit USD job\n\n{}".format('\n\n'.join(errors)) ,"Error")
        return False

    if scriptDialog.GetValue("SubmitUSDFileBox"):
        dlSubmission = False

    if PathUtils.IsPathLocal(usdFile) and dlSubmission:
        result = scriptDialog.ShowMessageBox("The USD file `{}` is local. Are you sure you want to continue?".format(usdFile),"Warning", ("Yes","No"))
        if(result=="No"):
            return False

    return True


def GetSettingsFilename():
    return Path.Combine(ClientUtils.GetUsersSettingsDirectory(),"USD.ini")


def SubmitButtonPressed(*args):
    global dlSubmission
    global scriptDialog
    global shotgunSettings

    if not CheckSubmissionParams():
        return

    frames = scriptDialog.GetValue("FramesBox")

    # Create job info file.
    jobInfoFilename = Path.Combine(ClientUtils.GetDeadlineTempPath(),"usd_job_info.job")
    writer = StreamWriter(jobInfoFilename, False, Encoding.Unicode)
    writer.WriteLine("Plugin=USD")
    writer.WriteLine("Name=%s"% scriptDialog.GetValue("NameBox"))
    writer.WriteLine("BatchName=%s"% scriptDialog.GetValue("BatchNameBox"))
    writer.WriteLine("Comment=%s"% scriptDialog.GetValue("CommentBox"))
    writer.WriteLine("Department=%s"% scriptDialog.GetValue("DepartmentBox"))
    writer.WriteLine("OutputDirectory0=%s"% os.path.dirname(scriptDialog.GetValue("OutputFileBox")))
    writer.WriteLine("Pool=%s"% scriptDialog.GetValue("PoolBox"))
    writer.WriteLine("SecondaryPool=%s"% scriptDialog.GetValue("SecondaryPoolBox"))
    writer.WriteLine("Group=%s"% scriptDialog.GetValue("GroupBox"))
    writer.WriteLine("Priority=%s"% scriptDialog.GetValue("PriorityBox"))
    writer.WriteLine("TaskTimeoutMinutes=%s"% scriptDialog.GetValue("TaskTimeoutBox"))
    writer.WriteLine("EnableAutoTimeout=%s"% scriptDialog.GetValue("AutoTimeoutBox"))
    writer.WriteLine("ConcurrentTasks=%s"% scriptDialog.GetValue("ConcurrentTasksBox"))
    writer.WriteLine("LimitConcurrentTasksToNumberOfCpus=%s"% scriptDialog.GetValue("LimitConcurrentTasksBox"))

    writer.WriteLine("MachineLimit=%s"% scriptDialog.GetValue("MachineLimitBox"))
    if(bool(scriptDialog.GetValue("IsBlacklistBox"))):
        writer.WriteLine("Blacklist=%s"% scriptDialog.GetValue("MachineListBox"))
    else:
        writer.WriteLine("Whitelist=%s"% scriptDialog.GetValue("MachineListBox"))

    writer.WriteLine("LimitGroups=%s"% scriptDialog.GetValue("LimitGroupBox"))
    writer.WriteLine("JobDependencies=%s"% scriptDialog.GetValue("DependencyBox"))
    writer.WriteLine("OnJobComplete=%s"% scriptDialog.GetValue("OnJobCompleteBox"))

    if(bool(scriptDialog.GetValue("SubmitSuspendedBox"))):
        writer.WriteLine("InitialStatus=Suspended")

    writer.WriteLine("ChunkSize=%s"% scriptDialog.GetValue("ChunkSizeBox"))

    if scriptDialog.GetValue("TileCB"):
        x_tile = scriptDialog.GetValue("XTileRange")
        y_tile = scriptDialog.GetValue("YTileRange")
        groups = re.findall(r"(\d+)", frames)

        if len(groups) == 1:
            end_frame = start_frame = int(groups[0])
        else:
            start_frame = int(groups[0])
            end_frame = int(groups[1])
        frame_count = end_frame - start_frame + 1

        frames ="{}-{}".format(start_frame, str(start_frame + (frame_count * x_tile * y_tile) - 1))

    writer.WriteLine("Frames=%s"% frames)

    writer.Close()

    # Create plugin info file.
    pluginInfoFilename = Path.Combine(ClientUtils.GetDeadlineTempPath(),"usd_plugin_info.job")
    writer = StreamWriter(pluginInfoFilename, False, Encoding.Unicode)

    if not bool(scriptDialog.GetValue("SubmitUSDFileBox")):
        writer.WriteLine("usdFile=%s"% scriptDialog.GetValue("usdFileBox"))
    writer.WriteLine("OutputFile=%s"% scriptDialog.GetValue("OutputFileBox"))
    writer.WriteLine("Threads=%s"% scriptDialog.GetValue("ThreadsBox"))
    writer.WriteLine("Verbose=%s"% scriptDialog.GetValue("VerboseBox"))
    writer.WriteLine("Version=%s"% scriptDialog.GetValue("VersionBox"))
    writer.WriteLine("Renderer=%s"% scriptDialog.GetValue("RendererBox"))
    writer.WriteLine("Executable=%s"% scriptDialog.GetValue("ExecutableBox"))

    renderSettings = scriptDialog.GetValue("RenderSettingBox")
    if not renderSettings:
        renderSettings ="/Render/rendersettings"
    writer.WriteLine("RenderSetting=%s"% renderSettings)

    if scriptDialog.GetValue("TileCB"):
        writer.WriteLine("TileOverrideEnable=%s"% scriptDialog.GetValue("TileCB"))
        writer.WriteLine("XTile=%s"% scriptDialog.GetValue("XTileRange"))
        writer.WriteLine("YTile=%s"% scriptDialog.GetValue("YTileRange"))
        writer.WriteLine("DeleteTiles=%s"% scriptDialog.GetValue("DeleteTilesCB"))
        writer.WriteLine("Frames=%s"% frames)

    if scriptDialog.GetValue("OverrideSizeCB"):
        writer.WriteLine("OverrideSizesEnable=%s"% scriptDialog.GetValue("OverrideSizeCB"))
        writer.WriteLine("WidthSize=%s"% scriptDialog.GetValue("WidthSizeRange"))
        writer.WriteLine("HeightSize=%s"% scriptDialog.GetValue("HeightSizeRange"))
        writer.WriteLine("ScaleSize=%s"% scriptDialog.GetValue("ScaleSizeRange"))


    if scriptDialog.GetValue("overrideCameraCB"):
        writer.WriteLine("CameraOverrideEnable=%s"% scriptDialog.GetValue("overrideCameraCB"))
        writer.WriteLine("Camera=%s"% scriptDialog.GetValue("CameraBox"))

    writer.WriteLine("ChunkSize=%s"% scriptDialog.GetValue("ChunkSizeBox"))

    writer.Close()

    # Setup the command line arguments.
    arguments = StringCollection()

    arguments.Add(jobInfoFilename)
    arguments.Add(pluginInfoFilename)

    if bool(scriptDialog.GetValue("SubmitUSDFileBox")):
        arguments.Add(scriptDialog.GetValue("usdFileBox"))

    # Now submit the job.
    results = ClientUtils.ExecuteCommandAndGetOutput(arguments)
    if dlSubmission:
        scriptDialog.ShowMessageBox(results,"Submission Results")

    print(results)


def GetExecutableVersions(excutable):
    plugin_config = RepositoryUtils.GetPluginConfig("USD")
    configKeys = plugin_config.GetConfigKeys()
    versionsList = []
    for item in configKeys:
        if excutable in str(item) and"_renderExecutable_"in str(item):
            versionsList.append(item.rsplit("_", 1)[-1])

    return versionsList


def GetExecutables():
    plugin_config = RepositoryUtils.GetPluginConfig("USD")
    configKeys = plugin_config.GetConfigKeys()
    executables = set()
    for item in configKeys:
        if"_renderExecutable_"in str(item):
            executables.add(item.split("_", 1)[0])

    return list(executables)


def Callbacks(*args):
    executableBox = scriptDialog.findChild(ComboControl.ComboControl,"ExecutableBox")
    tileBox = scriptDialog.findChild(CheckBoxControl.CheckBoxControl,"TileCB")
    resoultionBox = scriptDialog.findChild(CheckBoxControl.CheckBoxControl,"OverrideSizeCB")
    overrideCameraBox = scriptDialog.findChild(CheckBoxControl.CheckBoxControl,"overrideCameraCB")

    tileBox.stateChanged.connect(OnTileCBChanged)
    resoultionBox.stateChanged.connect(OnOverrideSizeChanged)
    overrideCameraBox.stateChanged.connect(OnOverrideCameraChanged)

    executableBox.currentTextChanged.connect(OnExecutableChanged)

def OnExecutableChanged(name):
    versionBox = scriptDialog.findChild(ComboControl.ComboControl,"VersionBox")
    versionBox.clear()
    items = GetExecutableVersions(name)
    versionBox.addItems(items)
    versionBox.setCurrentIndex(len(items) - 1)


def OnTileCBChanged(state):
    scriptDialog.SetEnabled("XTileRange", state)
    scriptDialog.SetEnabled("YTileRange", state)
    scriptDialog.SetEnabled("DeleteTilesCB", state)


def OnOverrideSizeChanged(state):
    scriptDialog.SetEnabled("WidthSizeRange", state)
    scriptDialog.SetEnabled("HeightSizeRange", state)
    scriptDialog.SetEnabled("ScaleSizeRange", state)
    scriptDialog.SetEnabled("ScaleSizeLabel", state)


def OnOverrideCameraChanged(state):
    scriptDialog.SetEnabled("CameraBox", state)

def OpenUsdview():
    executable = scriptDialog.GetValue("ExecutableBox")
    version = scriptDialog.GetValue("VersionBox")
    usd_file = scriptDialog.GetValue("usdFileBox")

    if not os.path.exists(usd_file):
        scriptDialog.ShowMessageBox("Please enter a valid usd file first, then launch usdview.")

    key = "{}_renderExecutable_{}".format(executable, version)
    plugin_config = RepositoryUtils.GetPluginConfig("USD")
    executable_path = plugin_config.GetConfigEntry(key)

    husk_path = extract_husk_path(executable_path)
    bin_dir = os.path.dirname(husk_path)
    arguments = [
        MapAndCleanPath(os.path.join(bin_dir, "hython")),
        MapAndCleanPath(os.path.join(bin_dir, "usdview")),
        MapAndCleanPath(usd_file),
    ]

    CallCommand(arguments)


def MapAndCleanPath(path):
    path = RepositoryUtils.CheckPathMapping(path)
    if SystemUtils.IsRunningOnWindows():
        path = path.replace("/", "\\")
        if path.startswith("\\") and not path.startswith("\\\\"):
            path = "\\" + path

    return path

def CallCommand(arguments):
    creationflags=0
    if os.name == 'nt':
        creationflags=0x08000000

    proc = subprocess.Popen(
        arguments,
        creationflags=creationflags,
    )
def extract_husk_path(text):
    current_os = os.name
    match = None
    if current_os == 'nt':  # Windows
        match = re.search(r'[A-Z]:\\[^\;]+husk\.exe', text)
    elif current_os == 'posix':
        if 'darwin' in os.uname().sysname.lower():  # macOS
            match = re.search(r'/Applications[^\;]+husk', text)
        else:  # Linux/Unix
            match = re.search(r'/opt[^\;]+husk', text)

    if match:
        return match.group(0)
    else:
        return None