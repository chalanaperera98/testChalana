import os
import subprocess
from pyrevit import script, forms

def check_for_updates():
    # Root folder of the extension
    extension_dir = os.path.dirname(__file__)
    # Repository subfolder (based on our previous check)
    repo_dir = os.path.join(extension_dir, "testChalana")
    git_exe = r"C:\Program Files\Git\bin\git.exe"

    if not os.path.exists(repo_dir):
        # Fallback if it's in the extension root
        repo_dir = extension_dir

    if os.path.exists(git_exe):
        try:
            # Run git pull silently
            process = subprocess.Popen(
                [git_exe, "-C", repo_dir, "pull", "origin", "main"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if "Already up to date" not in stdout and process.returncode == 0:
                # Update was successful and something changed
                print("Get Coordinates tool updated to the latest version.")
                forms.toast("Get Coordinates tool updated successfully!", title="Auto-Update Ready")
        except Exception as e:
            # Silently fail if there's an error during startup check
            pass

if __name__ == "__main__":
    check_for_updates()
