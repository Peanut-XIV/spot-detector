# Rebuilding the application for testing

Although python is an interpreted language (the code we write is[^1] the code
that is read by the computer when running an app), the packaging system we use
requires to rebuild the app every time we wish to introduce changes.

For that reason, before testing, we need to make sure  that the application
comes from the code we wish to test. In this step, we rebuild the application
to make sure the local changes are applied.

### Step 1:  activating the virtual environment
In the terminal, go to the directory containing the virtual environment
subdirectory made for this project. I personally keep it at the root of the
project directory. See this link if you need more information about
[python virtual environments](https://www.geeksforgeeks.org/python/python-virtual-environment/).

<details>
<summary>On Linux and macOS</summary>

```zsh
cd ~/where/you/keep/the/venv/directory/
```
If you run `ls -a`, you shoud see a directory named `venv` or `.venv`.
</details>

<details> <summary>On Windows</summary>

```cmd
cd ~\where\you\keep\the\venv\directory\
```
If you run `dir /a`, you shoud see a directory named `venv` or `.venv`.
</details>
<br>

Keep in mind however that a virtual environment can be created with
a custom name and could be called something other than `venv`. Then, activate
the python virtual environment. Make sure to use the correct name of the
virtual environment in the command.

<details> <summary>On Linux and macOS</summary>

```zsh
source ./venv/bin/activate
```
</details>

<details> <summary>On Windows</summary>

```cmd
.\venv\Scripts\activate
```
</details>

### Step 2: Rebuilding the application binary

Now go to the root of the project. It is also the root of the git repository.

<details> <summary>On Linux and macOS</summary>

```zsh
cd ~/where/you/keep/spot-detector/
```
If you run `ls -a`, you shoud see a directory named `venv` or `.venv`.
</details>

<details> <summary>On Windows</summary>

```cmd
cd ~\where\you\keep\spot-detector\
```
If you run `dir /a`, you shoud see a directory named `venv` or `.venv`.
</details>
<br>

You can now clean and rebuild PySide6 specific files for the project :

```zsh
pyside6-project clean
pyside6-project build
```

Finally, re-create the application :

<details>
<summary>
For a macOS .app bundle
</summary>

```zsh
pyside6-deploy -c ./macOS26_deploy.spec
```
</details>

<details>
<summary>
For a Linux application binary [Unavailable for now, WIP]
</summary>

```zsh
```
</details>

<details>
<summary>
For a Windows 11 desktop executable
</summary>

```zsh
pyside6-deploy -c ./win11_deploy.spec
```
</details>
<br>

[^1]: Not exactly true but a good enough approximation for the explanation
