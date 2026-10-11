"""Fake UnrealAutomationTool used by uebuild tests. Not a real UAT."""
import json
import os
import pathlib
import shutil
import sys


def arg_value(argv, prefix):
    for arg in argv:
        if arg.startswith(prefix):
            return arg[len(prefix):]
    return None


def main(argv):
    print("Running AutomationTool...")
    print("FakeUAT: BuildPlugin command detected" if "BuildPlugin" in argv
          else "FakeUAT: unexpected command")
    plugin = arg_value(argv, "-Plugin=")
    package = arg_value(argv, "-Package=")
    platforms = arg_value(argv, "-TargetPlatforms=") or "Win64"
    print("Plugin: %s" % plugin)
    print("Package: %s" % package)
    print("TargetPlatforms: %s" % platforms)

    fail_mode = os.environ.get("UEBUILD_FAKE_UAT_FAIL")

    if fail_mode == "warning":
        print("WARNING: Foo.cpp:12: something is deprecated")
        print("warning C4996: 'deprecatedFunc': was declared deprecated")

    if package:
        name = pathlib.Path(plugin).stem if plugin else "UnknownPlugin"
        dest = pathlib.Path(package) / name
        (dest / "Binaries").mkdir(parents=True, exist_ok=True)
        for platform in platforms.split("+"):
            (dest / "Binaries" / ("%s.dll" % platform)).write_text("fake binary")
        if plugin and pathlib.Path(plugin).is_file():
            shutil.copyfile(plugin, dest / pathlib.Path(plugin).name)
        else:
            (dest / (name + ".uplugin")).write_text(json.dumps({"FileVersion": 3}))
        filter_ini = pathlib.Path(package) / "FilterPlugin.ini"
        filter_ini.write_text("[FilterPlugin]\n")
        print("Packaged plugin at %s" % dest)

    if fail_mode == "error":
        print("ERROR: FakeCompiler exploded while compiling Foo.cpp")
        print("error C2660: 'Bar': function does not take 0 arguments")
        print("BUILD FAILED")
        print("AutomationTool exiting with ExitCode=6 (Error_Unknown)")
        return 6

    if fail_mode == "crash":
        print("Log output damaged, exiting without summary")
        return 137

    print("BUILD SUCCESSFUL")
    print("AutomationTool exiting with ExitCode=0 (Success)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
