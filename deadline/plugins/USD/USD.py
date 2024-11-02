#!/usr/bin/env python
import platform
import subprocess
import re
import json
import os

try:
    from pipes import quote
except ImportError:
    from shlex import quote

from Deadline.Plugins import DeadlinePlugin
from Deadline.Scripting import FileUtils, RepositoryUtils, SystemUtils
from System.IO import Path

combine_images_path = RepositoryUtils.GetRepositoryFilePath("plugins/USD/combine_images.py", True)
renderer_path = RepositoryUtils.GetRepositoryFilePath("plugins/USD/renderer.json", True)


def GetDeadlinePlugin():
    return USDPlugin()


def CleanupDeadlinePlugin(deadlinePlugin):
    deadlinePlugin.Cleanup()


def GetRendererSettings():
    with open(renderer_path, "r") as f:
        return json.load(f)


class USDPlugin(DeadlinePlugin):

    def __init__(self):
        self.InitializeProcessCallback += self.InitializeProcess
        self.RenderExecutableCallback += self.RenderExecutable
        self.RenderArgumentCallback += self.RenderArgument

    def Cleanup(self):
        for stdoutHandler in self.StdoutHandlers:
            del stdoutHandler.HandleCallback

        del self.InitializeProcessCallback
        del self.RenderExecutableCallback
        del self.RenderArgumentCallback

    def InitializeProcess(self):
        self.SingleFramesOnly = False
        self.StdoutHandling = True

        self._executable = self.GetPluginInfoEntryWithDefault("Executable", "husk")
        self._renderer = self.GetPluginInfoEntryWithDefault("Renderer", "Karma")
        self._rendererSettings = GetRendererSettings().get(self._executable, {})
        if not self._rendererSettings:
            self.FailRender('Renderer configration is missing in "{}" file'.format(renderer_path))
            return

        handlers = {
            "progress": self.HandleStdoutProgress,
            "done": self.HandleRenderFinish,
            "error": self.HandleStdoutError
        }

        rendererStout = self._rendererSettings.get("logs", {})
        for handler in handlers:
            for handler_pattern in rendererStout.get(handler, []):
                self.AddStdoutHandlerCallback(handler_pattern).HandleCallback += handlers.get(
                    handler)

    def RenderExecutable(self):
        version = self.GetPluginInfoEntryWithDefault("Version", "")

        executableStringKey = "{}_renderExecutable_{}".format(self._executable, version)
        print("Render Using:", executableStringKey)
        executableList = self.GetConfigEntry(executableStringKey)
        executable = FileUtils.SearchFileList(executableList)
        if not executable:
            self.FailRender('{executable} render executable was not found in the semicolon '
                            'separated list "{executableList}". The path to the render executable '
                            'can be configured from the Plugin Configuration in the Deadline '
                            'Monitor.'.format(executable=executable, executableList=executableList))

        return executable

    def RenderArgument(self):
        """
        Build up the render arguments we pass to the render executable
        :return: a string of render arguments
        """
        self.cmds = []
        usdFile = self.GetPluginInfoEntryWithDefault("usdFile", self.GetDataFilename()).strip().replace("\\", "/")

        frame = self.GetStartFrame()
        outputFile = self.GetPluginInfoEntry("OutputFile")
        self.formateCommandlineArgs(
            usdFile=self.MapAndCleanPath(usdFile),
            renderer=self._renderer,
            frameIncement=1,
            chunkSize=self.GetIntegerPluginInfoEntryWithDefault("ChunkSize", 1),
            renderSettings=self.GetPluginInfoEntryWithDefault("RenderSetting",
                                                              "/Render/rendersettings")
        )

        # Set the threads.
        threads = self.GetIntegerPluginInfoEntryWithDefault("Threads", 0)
        if threads > 0:
            self.LogInfo("Overriding render threads: " + str(threads))
            self.formateCommandlineArgs(threads=threads)

        self.formateCommandlineArgs(
            verbose="a{}".format(self.GetIntegerPluginInfoEntryWithDefault("Verbose", 0))
        )

        # res overrides
        if self.GetPluginInfoEntryWithDefault("OverrideSizesEnable", ""):
            self.formateCommandlineArgs(
                widthSize=str(self.GetPluginInfoEntry("WidthSize")),
                heightSize=str(self.GetPluginInfoEntry("HeightSize"))
            )
        self.formateCommandlineArgs(
            scaleSize=str(self.GetIntegerPluginInfoEntryWithDefault("ScaleSize", 100)))

        # camera overrides
        if self.GetBooleanPluginInfoEntryWithDefault("CameraOverrideEnable", False):
            self.formateCommandlineArgs(
                camera=self.GetPluginInfoEntryWithDefault("Camera", "/cameras/camera1")
            )

        # tiles
        if self.GetPluginInfoEntryWithDefault("TileOverrideEnable", ""):
            x_tile = self.GetIntegerPluginInfoEntryWithDefault("XTile", 0)
            y_tile = self.GetIntegerPluginInfoEntryWithDefault("YTile", 0)

            delete_tiles = self.GetBooleanPluginInfoEntryWithDefault("DeleteTiles", False)
            tile_count = int(x_tile) * int(y_tile)
            start_frame = int(re.findall(r"(\d+)", self.GetPluginInfoEntry("Frames"))[0])
            current_frame = self.GetStartFrame()

            frame = ((current_frame - start_frame) // tile_count) + start_frame
            index = (current_frame - frame) % tile_count

            output_path_resolved = self.substitute_frame_numbers(outputFile, frame)
            items = output_path_resolved.rsplit('.', 1)
            items.insert(1, self.substitute_frame_numbers("_tile%02d", index))
            items.insert(2, '.')
            tile_path = ''.join(items)
            outputFile = tile_path

            # post script
            post_script = '{} --add {} {}'.format(
                self.MapAndCleanPath(combine_images_path),
                self.MapAndCleanPath(tile_path),
                self.MapAndCleanPath(output_path_resolved)
            )
            if delete_tiles:
                post_script += ' --delete'

            self.formateCommandlineArgs(
                tileX=str(x_tile),
                tileY=str(y_tile),
                tileIndex=str(index),
                postRenderScript=post_script

            )

        self.formateCommandlineArgs(
            frameStart=str(frame),
            outputFile=outputFile
        )

        print("Arguments::", self.quoteCommandlineArgs(self.cmds))

        return self.quoteCommandlineArgs(self.cmds)

    @staticmethod
    def quoteCommandlineArgs(commandline):
        """
        A helper function used to quote commandline arguments as needed on a case-by-case basis (args with spaces, escape characters, etc.)
        :param commandline: The list of commandline arguments
        :return: a string composed of the commandline arguments, quoted properly
        """
        if platform.system() == "Windows":
            return subprocess.list2cmdline(commandline)
        else:
            return " ".join(quote(arg) for arg in commandline)

    def formateCommandlineArgs(self, **kwargs):

        for cmd in self._rendererSettings.get("args", {}):
            try:
                formatted_option = [c.format(**kwargs) for c in cmd]

                # one argument
                if len(formatted_option) == 1:
                    if formatted_option[0] not in self.cmds:
                        self.cmds.extend(formatted_option)
                else:
                    self.cmds.extend(formatted_option)
            except KeyError:
                continue

    def MapAndCleanPath(self, path):
        path = RepositoryUtils.CheckPathMapping(path)
        if SystemUtils.IsRunningOnWindows():
            path = path.replace("/", "\\")
            if path.startswith("\\") and not path.startswith("\\\\"):
                path = "\\" + path

        return path

    def substitute_frame_numbers(self, path_pattern, frame_number):
        substitutions = {
            "$F4": str(frame_number).zfill(4),
            "$F2": str(frame_number).zfill(2),
            "$F": str(frame_number).zfill(4),
            "<F>": str(frame_number).zfill(4),
            "<F2>": str(frame_number).zfill(2),
            "<F4>": str(frame_number).zfill(4),
            "%d": str(frame_number).zfill(4),
            "%02d": str(frame_number).zfill(2),
            "%04d": str(frame_number).zfill(4)
        }

        pattern = r"({})".format("|".join(substitutions))
        pattern = pattern.replace("$", "\$")
        pattern = re.compile(pattern)

        def replace(match):
            return substitutions[match.group(1)]

        return re.sub(pattern, replace, path_pattern)

    def HandleRenderFinish(self):
        self.SetProgress(100.0)

    def HandleStdoutProgress(self):
        self.SetStatusMessage(self.GetRegexMatch(0))
        self.SetProgress(float(self.GetRegexMatch(1)))

    def HandleStdoutError(self):
        self.FailRender(self.GetRegexMatch(0))
