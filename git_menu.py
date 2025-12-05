#!/usr/bin/env python3
import csv
import os
import shlex
import shutil
import subprocess
import sys

MENU = "1) ls  2) up  3) cd  4) edit  5) shell  a) apps  6) git status  7) git pull  8) git add  9) git commit  0) git push  q) quit"


def get_key():
    """Read a single keypress without requiring Enter."""
    if sys.platform.startswith("win"):
        import msvcrt

        ch = msvcrt.getch()
        try:
            return ch.decode("utf-8")
        except UnicodeDecodeError:
            return ""
    else:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def run(cmd):
    print(f"\n$ {' '.join(cmd)}")
    subprocess.run(cmd, check=False)


def launch_shell():
    if sys.platform.startswith("win"):
        # run(["cmd"])
        run(["pwsh"])
    else:
        # Use the user's preferred shell if set, otherwise fall back to /bin/sh.
        shell = os.environ.get("SHELL", "/bin/sh")
        run([shell])


def run_if_available(cmd):
    """Run a command if its executable exists on PATH."""
    if shutil.which(cmd[0]) is None:
        print(f"Command not found: {cmd[0]}")
        return False
    run(cmd)
    return True


def launch_terminal_app():
    cwd = os.getcwd()
    if sys.platform.startswith("win"):
        # Windows Terminal
        if not run_if_available(["wt", "-d", cwd]):
            print("Windows Terminal (wt) not found.")
        return

    candidates = [
        ["gnome-terminal", f"--working-directory={cwd}"],
        ["konsole", "--workdir", cwd],
        ["xfce4-terminal", "--working-directory", cwd],
        ["mate-terminal", f"--working-directory={cwd}"],
        ["lxterminal", "--working-directory", cwd],
        ["x-terminal-emulator", "--working-directory", cwd],
        ["alacritty", "--working-directory", cwd],
        ["kitty", "--directory", cwd],
        ["wezterm", "start", "--cwd", cwd],
    ]

    for cmd in candidates:
        if run_if_available(cmd):
            return

    print("No supported terminal launcher found.")


def apps_menu():
    top_cmd = ["wsl", "top"] if sys.platform.startswith("win") else ["top"]
    htop_cmd = ["wsl", "htop"] if sys.platform.startswith("win") else ["htop"]

    options = [
        ("1", "top", lambda: run_if_available(top_cmd)),
        ("2", "htop", lambda: run_if_available(htop_cmd)),
        ("3", "terminal", launch_terminal_app),
        ("4", "processes", processes_menu),
    ]

    print("\nApps:")
    for key, label, _ in options:
        print(f"  {key}) {label}")
    print("  q) back")

    sys.stdout.write("Choice: ")
    sys.stdout.flush()
    ch = get_key()
    print(ch)

    if ch.lower() == "q":
        return

    for key, _, action in options:
        if ch == key:
            action()
            return
    print("Invalid app selection.")


def fetch_processes(filter_text=""):
    procs = []
    try:
        if sys.platform.startswith("win"):
            try:
                output = subprocess.check_output(
                    ["tasklist", "/fo", "csv", "/nh"],
                    text=True,
                    stderr=subprocess.STDOUT,
                )
            except subprocess.CalledProcessError as exc:
                print(f"Could not list processes: {exc.output.strip()}")
                return []
            reader = csv.reader(output.splitlines())
            for row in reader:
                if len(row) < 2:
                    continue
                name, pid = row[0], row[1]
                try:
                    pid_int = int(pid)
                except ValueError:
                    continue
                procs.append((pid_int, name))
        else:
            try:
                output = subprocess.check_output(
                    ["ps", "-eo", "pid,comm"], text=True, stderr=subprocess.STDOUT
                )
            except subprocess.CalledProcessError as exc:
                print(f"Could not list processes: {exc.output.strip()}")
                return []
            lines = output.splitlines()
            if lines and lines[0].strip().lower().startswith("pid"):
                lines = lines[1:]
            for line in lines:
                parts = line.strip().split(None, 1)
                if len(parts) != 2:
                    continue
                pid_str, cmd = parts
                try:
                    pid_int = int(pid_str)
                except ValueError:
                    continue
                procs.append((pid_int, cmd))
    except OSError as exc:
        print(f"Could not list processes: {exc}")
        return []

    if filter_text:
        ft = filter_text.lower()
        procs = [(pid, name) for pid, name in procs if ft in name.lower()]

    procs.sort(key=lambda p: p[0])
    return procs


def stop_process(pid):
    if sys.platform.startswith("win"):
        cmd = ["taskkill", "/PID", str(pid)]
    else:
        cmd = ["kill", str(pid)]
    run(cmd)


def process_browser(title, allow_kill):
    page_size = 15
    page = 0
    filter_text = ""

    while True:
        procs = fetch_processes(filter_text)
        if not procs:
            if filter_text:
                print(f"No processes match '{filter_text}'.")
            else:
                print("No processes found.")
            return

        total = len(procs)
        max_page = max(0, (total - 1) // page_size)
        page = max(0, min(page, max_page))
        start = page * page_size
        chunk = procs[start : start + page_size]
        keys = [chr(ord("a") + i) for i in range(len(chunk))]

        print(
            f"\n{title} (showing {start + 1}-{start + len(chunk)} of {total})"
        )
        if filter_text:
            print(f"Filter: {filter_text}")
        for key, (pid, name) in zip(keys, chunk):
            print(f"  {key}) {name} (pid {pid})")

        print("n) next page  p) prev page  s) search  r) refresh  q) back")
        if allow_kill:
            print("Select a process key to stop it.")

        sys.stdout.write("Choice: ")
        sys.stdout.flush()
        ch = get_key()
        print(ch)
        cl = ch.lower()

        if cl == "q":
            return
        if cl == "n":
            if page < max_page:
                page += 1
            else:
                print("Already at last page.")
            continue
        if cl == "p":
            if page > 0:
                page -= 1
            else:
                print("Already at first page.")
            continue
        if cl == "s":
            filter_text = input("Filter text (blank to clear): ").strip()
            page = 0
            continue
        if cl == "r":
            continue

        if allow_kill:
            for key, (pid, _) in zip(keys, chunk):
                if ch == key:
                    stop_process(pid)
                    break
            else:
                print("Invalid selection.")
        else:
            if ch in keys:
                print("Use 'stop process' to terminate a process.")
            else:
                print("Invalid selection.")


def processes_menu():
    options = [
        ("1", "list processes", lambda: process_browser("Processes", False)),
        ("2", "stop process", lambda: process_browser("Stop process", True)),
    ]

    print("\nProcesses:")
    for key, label, _ in options:
        print(f"  {key}) {label}")
    print("  q) back")

    sys.stdout.write("Choice: ")
    sys.stdout.flush()
    ch = get_key()
    print(ch)

    if ch.lower() == "q":
        return

    for key, _, action in options:
        if ch == key:
            action()
            return
    print("Invalid processes selection.")


def choose_directory():
    page_size = 15
    page = 0
    filter_text = ""

    while True:
        try:
            entries = sorted(
                [name for name in os.listdir(".") if os.path.isdir(name)],
                key=str.lower,
            )
        except OSError as exc:
            print(f"Could not list directories: {exc}")
            return

        if filter_text:
            ft = filter_text.lower()
            entries = [name for name in entries if ft in name.lower()]

        if not entries:
            if filter_text:
                print(f"No directories match '{filter_text}'.")
            else:
                print("No directories found.")
            return

        total = len(entries)
        max_page = max(0, (total - 1) // page_size)
        page = max(0, min(page, max_page))
        start = page * page_size
        chunk = entries[start : start + page_size]
        keys = [chr(ord("a") + i) for i in range(len(chunk))]

        print(
            f"\nSelect directory (showing {start + 1}-{start + len(chunk)} of {total})"
        )
        if filter_text:
            print(f"Filter: {filter_text}")
        for key, name in zip(keys, chunk):
            print(f"  {key}) {name}")

        print("n) next page  p) prev page  s) search  r) refresh  q) back")
        sys.stdout.write("Choice: ")
        sys.stdout.flush()
        ch = get_key()
        print(ch)
        cl = ch.lower()

        if cl == "q":
            return
        if cl == "n":
            if page < max_page:
                page += 1
            else:
                print("Already at last page.")
            continue
        if cl == "p":
            if page > 0:
                page -= 1
            else:
                print("Already at first page.")
            continue
        if cl == "s":
            filter_text = input("Filter text (blank to clear): ").strip()
            page = 0
            continue
        if cl == "r":
            continue

        for key, name in zip(keys, chunk):
            if ch == key:
                try:
                    os.chdir(name)
                    print(f"Changed directory to: {os.getcwd()}")
                except OSError as exc:
                    print(f"Could not change directory: {exc}")
                return
        print("Invalid directory selection.")


def git_add_prompt():
    while True:
        try:
            output = subprocess.check_output(
                ["git", "status", "--porcelain"], text=True, stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as exc:
            print(f"Could not read git status: {exc.output.strip()}")
            return

        lines = [line.rstrip("\n") for line in output.splitlines() if line.strip()]
        if not lines:
            print("No changes to add.")
            return

        keys = [chr(c) for c in range(ord("a"), ord("z") + 1)] + list("0123456789")
        pairs = []

        for line in lines:
            status = line[:2]
            path = line[3:] if len(line) > 3 else ""
            if "->" in path:
                path = path.split("->", 1)[1].strip()
            pairs.append((status, path))

        if len(pairs) > len(keys):
            print(f"Showing first {len(keys)} of {len(pairs)} entries.")
        pairs_for_display = list(zip(keys, pairs))

        print("\nSelect file to add (q to exit):")
        for key, (status, path) in pairs_for_display:
            print(f"  {key}) {status} {path}")

        sys.stdout.write("Choice: ")
        sys.stdout.flush()
        ch = get_key()
        print(ch)

        if ch.lower() == "q":
            return

        for key, (status, path) in pairs_for_display:
            if ch == key:
                # First status column reflects staged state; "?" means untracked.
                staged = status[0] not in (" ", "?")
                if staged:
                    try:
                        subprocess.run(["git", "restore", "--staged", path], check=True)
                        print(f"Unstaged: {path}")
                    except subprocess.CalledProcessError as exc:
                        print(f"git restore --staged failed: {exc}")
                else:
                    try:
                        subprocess.run(["git", "add", path], check=True)
                        print(f"Added: {path}")
                    except subprocess.CalledProcessError as exc:
                        print(f"git add failed: {exc}")
                break
        else:
            print("Invalid file selection.")


def get_editor_command():
    env_editor = os.environ.get("GIT_MENU_EDITOR")
    if env_editor:
        return shlex.split(env_editor)
    if sys.platform.startswith("win"):
        editor = shutil.which("nvim")
        return [editor] if editor else None
    return ["nano"]


def edit_file_prompt():
    try:
        entries = sorted(
            [name for name in os.listdir(".") if os.path.isfile(name)],
            key=str.lower,
        )
    except OSError as exc:
        print(f"Could not list files: {exc}")
        return

    if not entries:
        print("No files found.")
        return

    keys = [chr(c) for c in range(ord("a"), ord("z") + 1)] + list("0123456789")
    if len(entries) > len(keys):
        print(f"Showing first {len(keys)} of {len(entries)} files.")
    pairs = list(zip(keys, entries))

    print("\nSelect file to edit (q to exit):")
    for key, name in pairs:
        print(f"  {key}) {name}")

    sys.stdout.write("Choice: ")
    sys.stdout.flush()
    ch = get_key()
    print(ch)

    if ch.lower() == "q":
        return

    for key, name in pairs:
        if ch == key:
            editor_cmd = get_editor_command()
            if not editor_cmd:
                print("No editor available (set GIT_MENU_EDITOR or install nvim).")
                return
            run(editor_cmd + [name])
            return
    print("Invalid file selection.")


def git_commit_prompt():
    message = input("Commit message (leave blank to cancel): ").strip()
    if not message:
        print("Commit cancelled.")
        return
    print(f"\n$ git commit -m \"{message}\"")
    try:
        subprocess.run(["git", "commit", "-m", message], check=True)
    except subprocess.CalledProcessError as exc:
        print(f"git commit failed: {exc}")


def main():
    print(f"cwd: {os.getcwd()}")
    print(MENU)
    while True:
        sys.stdout.write("\nSelect: ")
        sys.stdout.flush()
        ch = get_key()
        print(ch)  # echo the key pressed
        if ch == "1":
            if sys.platform.startswith("win"):
                # run(["cmd", "/c", "dir"])
                
                # powershell -Command "dir"
                # run(["powershell", "-Command", "dir"])
                run(["pwsh", "-Command", "dir"])

                # DIR /O:D /T:W
                # run(["cmd", "/c", "DIR", "/O:D", "/T:W"])
            else:
                run(["ls", "--color=auto"])
        elif ch == "2":
            try:
                os.chdir("..")
                print(f"Moved to parent: {os.getcwd()}")
            except OSError as exc:
                print(f"Could not move to parent: {exc}")
        elif ch == "3":
            choose_directory()
        elif ch == "4":
            edit_file_prompt()
        elif ch == "5":
            launch_shell()
        elif ch.lower() == "a":
            apps_menu()
        elif ch == "6":
            run(["git", "status"])
        elif ch == "7":
            run(["git", "pull"])
        elif ch == "8":
            git_add_prompt()
        elif ch == "9":
            git_commit_prompt()
        elif ch == "0":
            run(["git", "push"])
        elif ch.lower() == "q":
            print("Bye.")
            break
        else:
            print("Invalid choice.")
        print(f"\ncwd: {os.getcwd()}")
        print(MENU)


if __name__ == "__main__":
    main()
