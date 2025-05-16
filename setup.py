# setup.py
import os
import subprocess
import sys
import shutil

# --- Configuration ---
VENV_DIR = ".venv"  # Name of the virtual environment directory
PYTHON_REQUIREMENTS_FILE = "requirements.txt"
NODE_PACKAGE_JSON = "package.json"
# Specify desired Node.js version for nodeenv, e.g., "18.17.0", "lts", or leave None for nodeenv default
NODE_VERSION_FOR_NODEENV = "lts"
# --- End Configuration ---

# Platform-specific executable paths within the virtual environment
if os.name == 'nt':  # Windows
    VENV_PYTHON_EXEC = os.path.join(VENV_DIR, "Scripts", "python.exe")
    VENV_PIP_EXEC = os.path.join(VENV_DIR, "Scripts", "pip.exe")
    VENV_NODEENV_EXEC = os.path.join(VENV_DIR, "Scripts", "nodeenv.exe")
    NPM_CMD = os.path.join(VENV_DIR, "Scripts", "npm.cmd")
    NODE_EXEC = os.path.join(VENV_DIR, "Scripts", "node.exe") # nodeenv should place node here
else:  # Linux/macOS
    VENV_PYTHON_EXEC = os.path.join(VENV_DIR, "bin", "python")
    VENV_PIP_EXEC = os.path.join(VENV_DIR, "bin", "pip")
    VENV_NODEENV_EXEC = os.path.join(VENV_DIR, "bin", "nodeenv")
    NPM_CMD = os.path.join(VENV_DIR, "bin", "npm")
    NODE_EXEC = os.path.join(VENV_DIR, "bin", "node") # nodeenv should place node here

def run_command(command, cwd=None, check=True, shell=False, custom_env=None, capture=True):
    """Helper function to run a shell command."""
    print(f"Running command: {' '.join(command)}")
    try:
        process_env = os.environ.copy()
        if custom_env:
            process_env.update(custom_env)

        result = subprocess.run(
            command,
            cwd=cwd,
            check=check,
            capture_output=capture,
            text=True,
            env=process_env,
            shell=shell
        )
        if capture:
            if result.stdout:
                print(result.stdout.strip())
            if result.stderr and not check: # print stderr if check is False and there's an error
                print(result.stderr.strip(), file=sys.stderr)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(e.cmd)}")
        print(f"Return code: {e.returncode}")
        if capture:
            print(f"Stdout: {e.stdout.strip()}")
            print(f"Stderr: {e.stderr.strip()}")
        sys.exit(1) # Exit if a crucial command fails
    except FileNotFoundError:
        print(f"Error: Command not found: {command[0]}. Ensure it's installed and in PATH.")
        print("This can happen if the virtual environment is not set up correctly or a tool is missing.")
        sys.exit(1)

def is_python_env_set_up():
    """Checks if the Python virtual environment and key dependencies are set up."""
    if not os.path.exists(VENV_PIP_EXEC):
        print(f"Python virtual environment indicator ('{VENV_PIP_EXEC}') not found.")
        return False
    try:
        # Check if 'nodeenv' (a crucial Python package for this script) is installed in the venv
        run_command([VENV_PYTHON_EXEC, "-c", "import nodeenv"], capture=False) # Just check existence
        print("Python virtual environment and 'nodeenv' package appear to be set up.")
        return True
    except subprocess.CalledProcessError:
        print("'nodeenv' package not found in the Python virtual environment.")
        return False
    except FileNotFoundError: # VENV_PYTHON_EXEC itself not found
        print(f"Python virtual environment executable ('{VENV_PYTHON_EXEC}') not found.")
        return False

def is_node_env_set_up():
    """Checks if the Node.js environment (via nodeenv) is set up."""
    if not os.path.exists(NPM_CMD):
        print(f"Node.js NPM (via nodeenv at '{NPM_CMD}') not found.")
        return False
    if not os.path.exists(NODE_EXEC):
        print(f"Node.js executable (via nodeenv at '{NODE_EXEC}') not found.")
        return False
    try:
        # Verify npm and node can report their versions
        run_command([NPM_CMD, "--version"], capture=False)
        run_command([NODE_EXEC, "--version"], capture=False)
        print("Node.js environment (via nodeenv's npm and node) appears to be set up.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Node.js (npm or node) version check failed. Setup might be incomplete.")
        return False

def perform_python_setup():
    """Creates the Python virtual environment and installs dependencies."""
    print("\n--- Performing Python Virtual Environment Setup ---")
    if not os.path.exists(VENV_DIR):
        print(f"Creating Python virtual environment in '{VENV_DIR}'...")
        run_command([sys.executable, "-m", "venv", VENV_DIR]) # Use system python to create venv
    else:
        print(f"Python virtual environment '{VENV_DIR}' already exists.")

    # Install/update nodeenv first, as it's a core tool for this script
    print("Ensuring 'nodeenv' Python package is installed/updated in the virtual environment...")
    run_command([VENV_PIP_EXEC, "install", "--upgrade", "nodeenv"])

    if not os.path.exists(PYTHON_REQUIREMENTS_FILE):
        print(f"Warning: '{PYTHON_REQUIREMENTS_FILE}' not found. Skipping Python dependency installation (except nodeenv).")
    else:
        print(f"Installing/updating Python dependencies from '{PYTHON_REQUIREMENTS_FILE}'...")
        run_command([VENV_PIP_EXEC, "install", "--upgrade", "-r", PYTHON_REQUIREMENTS_FILE])
    
    print("Python setup phase complete.")

def perform_node_setup():
    """Sets up Node.js using nodeenv and installs npm packages."""
    print("\n--- Performing Node.js Environment Setup (via nodeenv) ---")
    if not os.path.exists(VENV_NODEENV_EXEC): # Should have been installed by perform_python_setup
        print(f"Error: 'nodeenv' executable not found at '{VENV_NODEENV_EXEC}'.")
        print("This indicates an issue with the Python setup phase.")
        sys.exit(1)

    print("Installing/Updating Node.js using 'nodeenv'...")
    nodeenv_command = [VENV_NODEENV_EXEC, "-p", "--force"] # -p integrates, --force overwrites if needed
    if NODE_VERSION_FOR_NODEENV:
        nodeenv_command.extend(["--node", NODE_VERSION_FOR_NODEENV])
    # nodeenv_command.append(VENV_DIR) # No, -p handles this.
    run_command(nodeenv_command)
    print("Node.js installation/update via 'nodeenv' complete.")

    if not os.path.exists(NODE_PACKAGE_JSON):
        print(f"Warning: '{NODE_PACKAGE_JSON}' not found. Skipping Node.js dependency installation.")
        return

    print(f"Installing/updating Node.js dependencies from '{NODE_PACKAGE_JSON}'...")
    project_root = os.getcwd()
    
    # Environment for npm to find its node
    venv_scripts_path = os.path.dirname(NPM_CMD)
    npm_env = os.environ.copy()
    npm_env["PATH"] = venv_scripts_path + os.pathsep + npm_env.get("PATH", "")

    lock_file_npm = os.path.join(project_root, "package-lock.json")
    if os.path.exists(lock_file_npm):
        print("Found 'package-lock.json', using 'npm ci' for clean, reproducible installs.")
        run_command([NPM_CMD, "ci"], cwd=project_root, custom_env=npm_env)
    else:
        print("No 'package-lock.json' found, using 'npm install'.")
        run_command([NPM_CMD, "install"], cwd=project_root, custom_env=npm_env)

    print("Node.js dependency installation phase complete.")

def print_activation_instructions():
    """Prints instructions on how to activate the virtual environment."""
    print("\n-----------------------------------------------------------")
    print("To activate the virtual environment, run:")
    if os.name == 'nt':
        print(f"  .\\{VENV_DIR}\\Scripts\\activate")
    else:
        print(f"  source ./{VENV_DIR}/bin/activate")
    print("Once activated, 'python', 'pip', 'node', and 'npm' commands will use the versions")
    print("isolated within this project's virtual environment.")
    print("-----------------------------------------------------------")

def main_setup_orchestrator():
    """Orchestrates the setup process, checking if steps are needed."""
    print("Starting environment integrity check...")

    python_ok = is_python_env_set_up()
    node_ok = is_node_env_set_up() # Check node status regardless of python, initially

    if python_ok and node_ok:
        print("\nEnvironment appears to be fully set up. No actions taken.")
        print_activation_instructions()
        return

    if not python_ok:
        perform_python_setup()
        # Re-check python status after attempting setup
        if not is_python_env_set_up():
            print("Critical: Python environment setup failed. Cannot proceed.")
            sys.exit(1)
        python_ok = True # Assume it's okay now for the next step
    else:
        print("\nPython part of the environment is already set up.")

    # Node.js setup depends on Python (for nodeenv).
    # So, if Python wasn't okay and was just set up, or if Python was okay but Node wasn't.
    if not node_ok: # Only proceed if node was not okay initially
        if not python_ok: # Should not happen due to above check, but as a safeguard
             print("Python environment is not ready. Skipping Node.js setup.")
        else:
            perform_node_setup()
            if not is_node_env_set_up():
                 print("Warning: Node.js environment setup might have had issues. Please check logs.")
    else:
        print("\nNode.js part of the environment is already set up.")

    print("\nSetup process finished.")
    print_activation_instructions()

if __name__ == "__main__":
    main_setup_orchestrator()
