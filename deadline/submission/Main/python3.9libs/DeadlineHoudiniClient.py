#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
import sys
import traceback

import hou

try:
    from CallDeadlineCommand import CallDeadlineCommand
except ImportError:
    path = ""
    print( "The CallDeadlineCommand.py script could not be found in the Houdini installation. Please make sure that the Deadline Client has been installed on this machine.\n" )
    hou.ui.displayMessage( "The CallDeadlineCommand.py script could not be found in the Houdini installation. Please make sure that the Deadline Client has been installed on this machine.", title="Submit Houdini To Deadline" )
else:
    path = CallDeadlineCommand([ "-GetRepositoryPath", "submission/Houdini/Main" ]).strip()

if path:
    path = path.replace( "\\", "/" )
    
    # Add the path to the system path
    if path not in sys.path:
        print("Appending \"" + path + "\" to system path to import SubmitHoudiniToDeadline module")
        sys.path.append( path )
    else:
        print( "\"%s\" is already in the system path" % path )

    # Import the script and call the main() function
    try:
        import SubmitHoudiniToDeadline
        SubmitHoudiniToDeadline.SubmitToDeadline()
    except:
        print( traceback.format_exc() )
        print( "The SubmitHoudiniToDeadline.py script could not be found in the Deadline Repository. Please make sure that the Deadline Client has been installed on this machine, that the Deadline Client bin folder is set in the DEADLINE_PATH environment variable, and that the Deadline Client has been configured to point to a valid Repository." )
else:
    print( "The SubmitHoudiniToDeadline.py script could not be found in the Deadline Repository. Please make sure that the Deadline Client has been installed on this machine, that the Deadline Client bin folder is set in the DEADLINE_PATH environment variable, and that the Deadline Client has been configured to point to a valid Repository." )
