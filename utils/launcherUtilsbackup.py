# -*- coding: utf-8 -*-
"""
Created on Fri Aug 12 06:51:37 2022

@author: Zed
"""
from datetime import datetime
from os.path import exists
from tkinter import filedialog
from utils import githubUtils
import json
import os
import pathlib
import progressbar
import requests
import shutil
import subprocess
import sys
import time
import tkinter as tk
import urllib.request
import zipfile
from appdirs import AppDirs
import platform
import stat


EXTRACT_ON_UPDATE = "true"
FILE_DATE_TO_CHECK = "gk.exe"
UPDATE_FILE_EXTENTION = ".zip"

# Folder where script is placed, It looks in this for the Exectuable
if getattr(sys, "frozen", False):
    LauncherDir = os.path.dirname(os.path.realpath(sys.executable))
elif __file__:
    LauncherDir = os.path.dirname(__file__)

extractOnUpdate = bool(str(EXTRACT_ON_UPDATE).replace("t", "T").replace("f", "F"))
ExecutableName = str(
    FILE_DATE_TO_CHECK
)  # Executable we're checking the 'modified' time of
FileExt = str(
    UPDATE_FILE_EXTENTION
)  # content_type of the .deb release is also "application\zip", so rely on file ext
FileIdent = ""  # If we ever get to multiple .zip files in a release, include other identifying information from the name
dirs = AppDirs(roaming=True)
currentOS = platform.system()
ModFolderPATH = os.path.join(dirs.user_data_dir, "OpenGOAL-Mods", "")
AppdataPATH = dirs.user_data_dir


pbar = None


def installedlist(PATH):
    print(PATH)
    scanDir = PATH
    directories = [
        d
        for d in os.listdir(scanDir)
        if os.path.isdir(os.path.join(os.path.abspath(scanDir), d))
    ]
    print(directories)
    for i in directories:
        print(i)
    print(os.path.dirname(os.path.dirname(PATH)))


def show_progress(block_num, block_size, total_size):
    if total_size > 0:
        global pbar
        if pbar is None:
            pbar = progressbar.ProgressBar(maxval=total_size)
            pbar.start()

        downloaded = block_num * block_size

        if downloaded < total_size:
            pbar.update(downloaded)
        else:
            pbar.finish()
            pbar = None


def process_exists(process_name):
    call = "TASKLIST", "/FI", "imagename eq %s" % process_name
    try:
        # use buildin check_output right away
        output = subprocess.check_output(call).decode()
        # check in last line for process name
        last_line = output.strip().split("\r\n")[-1]
        # because Fail message could be translated
        return last_line.lower().startswith(process_name.lower())
    except:
        return False


def try_kill_process(process_name):
    if process_exists(process_name):
        os.system("taskkill /f /im " + process_name)


def try_remove_file(file):
    if exists(file):
        os.remove(file)


def try_remove_dir(dir):
    if exists(dir):
        shutil.rmtree(dir)


def local_mod_image(MOD_ID):
    path = ModFolderPATH + MOD_ID + "\\ModImage.png"
    if exists(path):
        return path
    return None


def launch_local(MOD_ID, GAME):
    try:
        # Close Gk and goalc if they were open.
        try_kill_process("gk.exe")
        try_kill_process("goalc.exe")

        time.sleep(1)
        InstallDir = ModFolderPATH + MOD_ID

        UniversalIsoPath = AppdataPATH + "\OpenGOAL\jak1\mods\data\iso_data"
        
        GKCOMMANDLINElist = [
            os.path.abspath(InstallDir + "\gk.exe"),  # Using os.path.abspath to get the absolute path.
            "--proj-path",
            os.path.abspath(InstallDir + "\\data"),  # Using absolute path for data folder too.
            "-boot",
            "-fakeiso",
            "-v",
        ]
        if(GAME == "jak2"):
            GKCOMMANDLINElist = [
            InstallDir + "\gk.exe",
            "--proj-path",
            InstallDir + "\\data",
            "-boot",
            "-fakeiso",
            "-v",
            "--game",
            "jak2",
            "debug",
        ]
        print(GKCOMMANDLINElist)
        subprocess.Popen(GKCOMMANDLINElist, shell=True, cwd=os.path.abspath(InstallDir))
    except Exception as e:  # Catch all exceptions and print the error message.
        return str(e)


def openFolder(path):
    FILEBROWSER_PATH = os.path.join(os.getenv("WINDIR"), "explorer.exe")
    subprocess.run([FILEBROWSER_PATH, path])


def reinstall(MOD_ID):
    InstallDir = ModFolderPATH + MOD_ID
    AppdataPATH = os.getenv("APPDATA")
    UniversalIsoPath = AppdataPATH + "\OpenGOAL\jak1\mods\data\iso_data"
    
    GKCOMMANDLINElist = [
        InstallDir + "\gk.exe",
        "--proj-path",
        InstallDir + "\\data",
        "-boot",
        "-fakeiso",
        "-v",
    ]

    # if ISO_DATA has content, store this path to pass to the extractor
    if exists(UniversalIsoPath + r"\jak1\Z6TAIL.DUP"):
        iso_path = UniversalIsoPath + "\jak1"
        
    else:
        # if ISO_DATA is empty, prompt for their ISO and store its path.
        root = tk.Tk()
        print("Please select your iso.")
        root.title("Select ISO")
        root.geometry("230x1")
        iso_path = filedialog.askopenfilename()
        root.destroy()
        if pathlib.Path(iso_path).is_file:
            if not (pathlib.Path(iso_path).suffix).lower() == ".iso":
                1 / 0

    # Close Gk and goalc if they were open.
    try_kill_process("gk.exe")
    try_kill_process("goalc.exe")
    print("Done update starting extractor\n")
    if currentOS == "Windows":
        extractor_command_list = [
            os.path.join(InstallDir, "extractor.exe"),
            "-f",
            iso_path,
        ]
    if currentOS == "Linux":
        # We need to give the executibles execute permissions in Linux but this doesn't work
        # chmod_command_list = ["cd" + os.path.join(LauncherDir), "chmod +x extractor goalc gk"]
        # subprocess.Popen(chmod_command_list)
        os.chmod(os.path.join(LauncherDir, "extractor"), stat.S_IXOTH)
        print("Done chmods!")
        # Then we need to call the Linux extractor when we do the next Popen
        extractor_command_list = [
            os.path.join(LauncherDir),
            "./extractor -f" + iso_path + "--proj-path" + InstallDir,
        ]
    print(extractor_command_list)

    subprocess.Popen(extractor_command_list, shell=True, cwd=os.path.abspath(InstallDir))

    # wait for extractor to finish
    while process_exists("extractor.exe"):
        print("extractor.exe still running, sleeping for 1s")
        time.sleep(1)

    # move the extrated contents to the universal launchers directory for next time.
    if not (exists((UniversalIsoPath + r"\jak1\Z6TAIL.DUP"))):
        
        # os.makedirs(AppdataPATH + "\OpenGOAL-Launcher\data\iso_data")
        print("The new directory is created!")
        shutil.move(InstallDir + "/data/iso_data", "" + UniversalIsoPath + "")
        
        # try_remove_dir(InstallDir + "/data/iso_data")
        # os.symlink("" + UniversalIsoPath +"", InstallDir + "/data/iso_data")


def replaceText(path, search_text, replace_text):
    # Check if the file exists
    if not os.path.isfile(path):
        print(f"File '{path}' does not exist.")
        return

    # Open the file in read-only mode
    with open(path, "r") as file:
        data = file.read()

    # Perform the search and replace operation
    data = data.replace(search_text, replace_text)

    # Open the file in write mode to write the replaced content
    with open(path, "w") as file:
        file.write(data)

    print(f"Text replaced successfully in file '{path}'.")


def launch(URL, MOD_ID, MOD_NAME, LINK_TYPE,GAME):
    print(GAME)
    print(GAME)
    print(GAME)
    print(GAME)
    print(GAME)
    print(GAME)
    print(GAME)
    print(GAME)
    print(GAME)
    print(GAME)
    print(GAME)
    print(GAME)
    if URL is None:
        return

    # start of update check method
    # Github API Call
    launchUrl = URL
    if LINK_TYPE == githubUtils.LinkTypes.BRANCH:
      launchUrl = githubUtils.branchToApiURL(URL)
    LatestRelAssetsURL = ""

    print("\nlaunching from " + launchUrl)
    PARAMS = {"address": "yolo"}
    r = json.loads(json.dumps(requests.get(url=launchUrl, params=PARAMS).json()))

    # paths
    InstallDir = ModFolderPATH + MOD_ID
    AppdataPATH = os.getenv("APPDATA")
    UniversalIsoPath = AppdataPATH + "\OpenGOAL\jak1\mods\data\iso_data"
    
    GKCOMMANDLINElist = [
        InstallDir + "\gk.exe",
        "--proj-path",
        InstallDir + "\\data",
        "-boot",
        "-fakeiso",
        "-v",
    ]

    if (GAME == "jak2"):
        GKCOMMANDLINElist = [
        InstallDir + "\gk.exe",
        "--proj-path",
        InstallDir + "\\data",
        "-boot",
        "-fakeiso",
        "-v",
        "--game",
        "jak2",
        "debug",
    ]

    # store Latest Release and check our local date too.
    if LINK_TYPE == githubUtils.LinkTypes.BRANCH:
      LatestRel = datetime.strptime(
          r.get("commit")
          .get("commit")
          .get("author")
          .get("date")
          .replace("T", " ")
          .replace("Z", ""),
          "%Y-%m-%d %H:%M:%S",
      )
      LatestRelAssetsURL = githubUtils.branchToArchiveURL(URL)
    elif LINK_TYPE == githubUtils.LinkTypes.RELEASE:
      LatestRel = datetime.strptime(
          r[0].get("published_at").replace("T", " ").replace("Z", ""),
          "%Y-%m-%d %H:%M:%S",
      )
      assets = json.loads(json.dumps(requests.get(url=r[0].get("assets_url"), params=PARAMS).json()))
      for asset in assets:
        if "linux" not in asset.get("name") and "macos" not in asset.get("name") and "json" not in asset.get("name"):
          LatestRelAssetsURL = asset.get("browser_download_url")
          break
      
      # response = requests.get(url=LatestRelAssetsURL, params=PARAMS)
      # content_type = response.headers["content-type"]

    LastWrite = datetime(2020, 5, 17)
    if exists(InstallDir + "/" + ExecutableName):
        LastWrite = datetime.utcfromtimestamp(
            pathlib.Path(InstallDir + "/" + ExecutableName).stat().st_mtime
        )

    # update checks

    if(GAME == "jak1"):
        NotExtracted = bool(not (exists(UniversalIsoPath + "\\" + GAME + "\Z6TAIL.DUP")))
        NotCompiled = bool(not (exists(InstallDir + r"\data\out\jak1\fr3\GAME.fr3")))
        needUpdate = bool((LastWrite < LatestRel) or (NotExtracted) or NotCompiled)
    if(GAME == "jak2"):
        NotExtracted = bool(not (exists(UniversalIsoPath + "\\" + GAME + "\Z6TAIL.DUP")))
        NotCompiled = bool(not (exists(InstallDir + r"\data\out\jak2\fr3\GAME.fr3")))
        needUpdate = bool((LastWrite < LatestRel) or (NotExtracted) or NotCompiled)

    print("Currently installed version created on: " + LastWrite.strftime('%Y-%m-%d %H:%M:%S'))
    print("Newest version created on: " + LatestRel.strftime('%Y-%m-%d %H:%M:%S'))
    if(NotExtracted):
        print("Error! Iso data does not appear to be extracted to " + UniversalIsoPath + "\\" + GAME + "\Z6TAIL.DUP")
        print("Will ask user to provide ISO")
    if(NotCompiled):
        print("Error! The game is not compiled")
    if((LastWrite < LatestRel)):
        print("Looks like we need to download a new update!")
        print(LastWrite)
        print(LatestRel)
        print("Is newest posted update older than what we have installed? " + str((LastWrite < LatestRel)))

    if(GAME == "jak1"):
        # attempt to migrate any old settings files from using MOD_NAME to MOD_ID
        if exists(AppdataPATH + "\OpenGOAL\jak1\settings\\" + MOD_NAME + "-settings.gc"):
            # just to be safe delete the migrated settings file if it already exists (shouldn't happen but prevents rename from failing below)
            if exists(AppdataPATH + "\OpenGOAL\jak1\settings\\" + MOD_ID + "-settings.gc"):
                os.remove(
                    AppdataPATH + "\OpenGOAL\jak1\settings\\" + MOD_ID + "-settings.gc"
                )

            # rename settings file
            os.rename(
                AppdataPATH + "\OpenGOAL\jak1\settings\\" + MOD_NAME + "-settings.gc",
                AppdataPATH + "\OpenGOAL\jak1\settings\\" + MOD_ID + "-settings.gc",
            )
        # force update to ensure we recompile with adjusted settings filename in pckernel.gc
        needUpdate = True
        
    if (needUpdate):
        
        #start the actual update method if needUpdate is true
        print("\nNeed to update")
        print("Starting Update...")
        # Close Gk and goalc if they were open.
        try_kill_process("gk.exe")
        try_kill_process("goalc.exe")

        # download update from github
        # Create a new directory because it does not exist
        try_remove_dir(InstallDir + "/temp")
        if not os.path.exists(InstallDir + "/temp"):
            print("Creating install dir: " + InstallDir)
            os.makedirs(InstallDir + "/temp")
            
        response = requests.get(LatestRelAssetsURL)
        if response.history:
            print("Request was redirected")
            for resp in response.history:
                print(resp.status_code, resp.url)
                print("Final destination:")
                print(response.status_code, response.url)
                LatestRelAssetsURL = response.url

        else:
            print("Request was not redirected")

        print("Downloading update from " + LatestRelAssetsURL)
        file = urllib.request.urlopen(LatestRelAssetsURL)
        print()
        print(str("File size is ") + str(file.length))
        urllib.request.urlretrieve(
            LatestRelAssetsURL, InstallDir + "/temp/updateDATA.zip", show_progress
        )
        print("Done downloading")
        r = requests.head(LatestRelAssetsURL, allow_redirects=True)

        # delete any previous installation
        print("Removing previous installation " + InstallDir)
        try_remove_dir(InstallDir + "/data")
        try_remove_dir(InstallDir + "/.github")
        try_remove_file(InstallDir + "/gk.exe")
        try_remove_file(InstallDir + "/goalc.exe")
        try_remove_file(InstallDir + "/extractor.exe")
        try_remove_file(InstallDir + "/decompiler.exe")


        #if ISO_DATA has content, store this path to pass to the extractor
        if (exists(UniversalIsoPath + "\\" + GAME + "\Z6TAIL.DUP")):
            
            print("We found ISO data from a previous mod installation! Lets use it!")
            print("Found in " + UniversalIsoPath + "\\" + GAME + "\Z6TAIL.DUP")
            iso_path = UniversalIsoPath + "\\" +GAME
        else:
            #if ISO_DATA is empty, prompt for their ISO and store its path.

            #cleanup and remove a corrupted iso
            if os.path.exists(UniversalIsoPath + "\\" + GAME) and os.path.isdir(UniversalIsoPath + "\\" + GAME):
                print("Removing corrupted iso destination... " + UniversalIsoPath + "\\" + GAME + "")
                shutil.rmtree(UniversalIsoPath + "\\" + GAME)
                print("corrupt iso removed.")

            print("Looking for some ISO data in " + UniversalIsoPath + "\\" +GAME)
            
            print("We did not find ISO data from a previous mod, lets ask for some!")
            # prompt for ISO file
            root = tk.Tk()
            root.title("Select ISO")
            root.geometry("230x1")
            
            top_level = tk.Toplevel(root)
            top_level.attributes("-topmost", True)  # Set the file dialog to stay on top
            
            iso_path = filedialog.askopenfilename(parent=top_level)
            root.destroy()
            if pathlib.Path(iso_path).is_file:
                if not (pathlib.Path(iso_path).suffix).lower() == ".iso":
                    1 / 0
        # extract update
        print("Extracting update")
        TempDir = InstallDir + "/temp"
        with zipfile.ZipFile(TempDir + "/updateDATA.zip", "r") as zip_ref:
            zip_ref.extractall(TempDir)

        # delete the update archive
        try_remove_file(TempDir + "/updateDATA.zip")

        SubDir = TempDir
        if LINK_TYPE == githubUtils.LinkTypes.BRANCH or len(os.listdir(SubDir)) == 1:
            # for branches, the downloaded zip puts all files one directory down
            SubDir = SubDir + "/" + os.listdir(SubDir)[0]

        print("Moving files from " + SubDir + " up to " + InstallDir)
        allfiles = os.listdir(SubDir)
        for f in allfiles:
            shutil.move(SubDir + "/" + f, InstallDir + "/" + f)
        try_remove_dir(TempDir)

        if(GAME=="jak1"):
            replaceText(
                InstallDir + r"\data\goal_src\jak1\pc\pckernel.gc",
                "Playing Jak and Daxter: The Precursor Legacy",
                "Playing " + MOD_NAME,
            )
            replaceText(
                InstallDir + r"\data\goal_src\jak1\pc\pckernel.gc",
                "/pc-settings.gc",
                r"/" + MOD_ID + "-settings.gc",
            )

        # if extractOnUpdate is True, check their ISO_DATA folder

        # Close Gk and goalc if they were open.
        try_kill_process("gk.exe")
        try_kill_process("goalc.exe")
        print("Done update starting extractor This one can take a few moments! \n")
        
        #extract and compile, but dont boot the game so we can move the iso files
        
        if(GAME == "jak1"):
            extractor_command_list = [InstallDir + "\extractor.exe", "-f", iso_path , "-e", "-v", "-d", "-c"]
            print(extractor_command_list)
            subprocess.Popen(extractor_command_list, shell=True, cwd=os.path.abspath(InstallDir))

            # move the extrated contents to the universal launchers directory for next time.
            
        while process_exists("extractor.exe"):
            print("extractor.exe still running, sleeping for 1s")
            time.sleep(1)

        if(GAME == "jak2"):
            decompiler_command_list = [InstallDir + "\decompiler.exe", 
                                       "./data/decompiler/config/jak2/jak2_config.jsonc", 
                                       iso_path, 
                                       "./data/decompiler_out", 
                                       "--version"
                                       "\"ntsc_v1\"",
                                       "--config-override",
                                       "{\"decompile_code\": false}"]
            print(decompiler_command_list)
            subprocess.Popen(decompiler_command_list, shell=True, cwd=os.path.abspath(InstallDir))

            # move the extrated contents to the universal launchers directory for next time.
            if not (exists((UniversalIsoPath + "\\" + GAME + "\Z6TAIL.DUP"))):
                while process_exists("decompiler.exe"):
                    print("decompiler.exe still running, sleeping for 1s")
                    time.sleep(1)

            
        if not os.path.exists(UniversalIsoPath + "\\" + GAME):
            shutil.move(InstallDir + "/data/iso_data"+ "\\" + GAME, UniversalIsoPath)
            print("copying " + InstallDir + "/data/iso_data"+ "\\" + GAME + "to " + UniversalIsoPath )

        #keep checking to make sure the move is in a finished state
        while not (exists((UniversalIsoPath + "\\" + GAME + "\Z6TAIL.DUP"))):
            print("waiting for iso at " + UniversalIsoPath + "\\" + GAME + "\Z6TAIL.DUP")
            time.sleep(1)
        
        if(NotExtracted):
            print("Error! Iso data does not appear to be extracted to " + UniversalIsoPath + "\\" + GAME + "\Z6TAIL.DUP")
            print("Will ask user to provide ISO")
        if(NotCompiled):
            print("Error! The game is not compiled")
        if((LastWrite < LatestRel)):
            print("Looks like we need to download a new update!")
            print(LastWrite)
            print(LatestRel)
            print("Is newest posted update older than what we have installed? " + str((LastWrite < LatestRel)))

        #ok launch game :D
        subprocess.Popen(GKCOMMANDLINElist, shell=True, cwd=os.path.abspath(InstallDir))

    else:
        # if we dont need to update, then close any open instances of the game and just launch it
        print("Game is up to date!")
        print("Launching now!")
        launch_local(MOD_ID, GAME)