# PCCtrl
Easy To Use PC Control, with a local server making it possible to control the pc directly from your phone.

## Requirements:
1. You will need the programming language **Python**, which you can download [here](https://www.python.org). This is required to run the program.

## Instructions:
1. Download the [installer](https://github.com/chunkberries/PC-Ctrl/releases/download/Installer/PCCtrlSetup.exe).
2. When running the installer you will be prompted to select the users path. To change the user you wanna control, click browse.
<img width="602" height="465" alt="ctrltut2" src="https://github.com/user-attachments/assets/ffca8d37-ad3b-4cd5-9b32-84bcad93de4c" />

3. To get all the names of all the users on the pc, open up a **Command Prompt** and run:
  ```net user```

4. When you've found the user you wanna control, see the image where you need to put the user's name.
<img width="423" height="439" alt="ctrltut1" src="https://github.com/user-attachments/assets/1237c78e-fdfd-438f-86e3-502aabe88562" />

5. After that, click **OK** and hit **Next** then **Install**.
6. Ater the installation you have the option to run the PCCtrl server. This just starts the control making you able to visit the control panel, note that this starts the control for the logged in user, not the user you selected. This is recommended if you wanna test the control to make sure everything works.

### Now you've successfully installed the server onto the pc! This next step will guide you how to set a pin to access the control panel.

**Setting a pin:**
1. Go to **C:/PCCtrl**. In here you should see the file called **remote_server.py**. Right click  and select **Open with: Notepad**. At the top you should see the variable **PIN**, change that to your liking. Make sure your pins starts and ends with double-quotes (" "), otherwise the code will error.
2. Hit **CTRL + S** to save.

### Now you've set a pin! Let's move onto actually opening the control panel.

If you selected the option "Start PCCtrl server" during installation, you can proceed with the steps below, if not, just log in with the user you chose during installation to start the server, note that it might take a minute or two for the program to start.

1. First of all you have to get the PC's ip adress. To do that, open a **Command Prompt** and run:
```ipconfig```
2. Look for "IPv4 Adress". Thats the ip.
3. Once you've got the ip, go onto your phone and type in **<the pc's ip>:5050** (the default port is 5050, change it if you've changed it through the python code)

If you've done everything correctly, you have now access to the control panel. 

### Shutting down the server
1. Open task manager.
2. Search for "python" and stop all the processes that comes up.

A quicker and easier way will probably come in future updates, but I'll keep it like this for now.

### Logging

To check the **logs** of all the actions, simple go to C:/PCCtrl, where there will be a file named **remote_actions.log**. If you don't see it, don't worry, this just means that you haven't performed any actions yet.

### Uninstalling

To uninstall PCCtrl, go to C:/PCCtrl where you will find a file named **unins000.exe**. Simply run that first, shutdown the server following the steps above, and then delete the PCCtrl folder from you C: drive.
In future updates this process will also become quicker and easier.

If something doesn't work, feel free to message me on discord: **chunkberries**
