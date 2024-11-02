import os
import json
import hou

from CallDeadlineCommand import CallDeadlineCommand, GetDeadlineCommand


class UsdSubmit:
    def __init__(self):
        self.settings = {}

    def get_deadline_command(self):
        deadline_command = GetDeadlineCommand()

        if not deadline_command or os.path.exists(deadline_command):
            raise ("The DeadlineCommand script could not be found. "
                   "Please make sure that the Deadline Client has been installed on this machine, "
                   "that the Deadline Client bin folder is set in the DEADLINE_PATH environment "
                   "variable, and that the Deadline Client has been configured to point to a "
                   "valid Repository.")

        return deadline_command

    def get_submission_script(self):
        script_path = CallDeadlineCommand(["-GetRepositoryFilePath ", "scripts/Submission"
                                                                      "/USDSubmission.py"]).strip()

        if not os.path.isfile(script_path):
            raise ("The USDSubmission.py script could not be found in the Deadline Repository. "
                   "Please make sure that the Deadline Client has been installed on this machine, "
                   "that the Deadline Client bin folder is set in the DEADLINE_PATH environment "
                   "variable, and that the Deadline Client has been configured to point to a "
                   "valid Repository.")

        return script_path

    def submit(self):
        res = CallDeadlineCommand(
            ["-ExecuteScript", self.get_submission_script(), json.dumps(self.settings)],
            False
        )
        print(self.settings)
        return res


class HouUsdSubmit(UsdSubmit):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.settings = {}
        self.update_settings()

    def get_settings(self, parm_name):
        return self.node.parm(parm_name).eval()

    def get_settings_str(self, parm_name):
        return self.node.parm(parm_name).evalAsString()

    def get_frame_range(self):
        if self.get_settings("trange") == 0:
            return int(hou.frame())
        else:
            start, end, step = self.node.parmTuple("f").eval()
            return "{}-{}:{}".format(int(start), int(end), int(step))

    def get_output(self):
        output = self.get_settings("output_render")
        output = output.replace(".{}.".format(int(hou.frame())), ".$F.")
        return output

    def set_rendersettings_overrides(self):
        option = self.get_settings("override_res")
        if option == "specific":

            res = self.node.parmTuple("res_user").eval()
            self.settings.update({
                "OverrideSizesEnable": True,
                "WidthSizeRange": res[0],
                "HeightSizeRange": res[1],
                "ScaleSizeRange": 100,
            })
        elif option == "scale":
            self.settings.update({
                "ScaleSizeRange": self.get_settings("res_scale"),
            })
        else:
            self.settings.update({
                "OverrideSizeCB": False,
                "ScaleSizeRange": 100,
            })

    def update_settings(self):
        self.settings.update(
            {
                "NameBox": self.get_settings("job_name"),
                "BatchNameBox": self.get_settings("batch_name"),
                "CommentBox": self.get_settings("comment"),
                "DepartmentBox": self.get_settings("department"),
                "PoolBox": self.get_settings("pool"),
                "SecondaryPoolBox": self.get_settings("secondary_pool"),
                "GroupBox": self.get_settings("group"),
                "PriorityBox": self.get_settings("priority"),
                "TaskTimeoutBox": self.get_settings("task_timeout"),
                "AutoTimeoutBox": self.get_settings("auto_task_timeout"),
                "ConcurrentTasksBox": self.get_settings("concurrent_tasks"),
                "LimitConcurrentTasksBox": self.get_settings("slave_task_limit"),
                "MachineLimitBox": self.get_settings("machine_limit"),
                "IsBlacklistBox": self.get_settings("blacklist"),
                "MachineListBox": self.get_settings("machine_list"),
                "LimitGroupBox": self.get_settings("limits"),
                "DependencyBox": self.get_settings("dependencies"),
                "OnJobCompleteBox": self.get_settings("on_complete"),
                "SubmitSuspendedBox": self.get_settings("submit_suspended"),
                "VerboseBox": self.get_settings_str("verbose"),
                "ThreadsBox": self.get_settings("threads"),
                "ChunkSizeBox": self.get_settings("chunk_size"),
                "SubmitUSDFileBox": self.get_settings("submit_usd_files"),

                # USD
                "usdFileBox": self.get_settings("usd_file"),
                "RenderSettingBox": self.get_settings("render_settings"),
                "OverrideSizeCB": bool(self.get_settings("camera")),
                "CameraBox": self.get_settings("camera"),
                "ExecutableBox": self.get_settings_str("executable"),
                "VersionBox": self.get_settings_str("version"),
                "RendererBox": self.get_settings_str("renderer"),

                # Tiles
                "TileCB": self.get_settings("tiles_enabled"),
                "XTileRange": self.get_settings("x_tiles"),
                "YTileRange": self.get_settings("y_tiles"),
                "DeleteTilesCB": self.get_settings("cleanup_tiles"),

            }
        )

        self.settings["FramesBox"] = self.get_frame_range()
        self.settings["OutputFileBox"] = self.get_output()

        self.set_rendersettings_overrides()
