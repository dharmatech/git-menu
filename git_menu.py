#!/usr/bin/env python3
import os
import subprocess
import sys

MENU = "1) git status  2) git pull  3) list files  4) shell  5) up  6) cd  7) git add  8) git commit  9) git push  q) quit"


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
        run(["cmd"])
    else:
        # Use the user's preferred shell if set, otherwise fall back to /bin/sh.
        shell = os.environ.get("SHELL", "/bin/sh")
        run([shell])


def choose_directory():
    try:
        entries = sorted(
            [name for name in os.listdir(".") if os.path.isdir(name)],
            key=str.lower,
        )
    except OSError as exc:
        print(f"Could not list directories: {exc}")
        return

    if not entries:
        print("No directories found.")
        return

    # Build a keymap: a, b, c, ..., 0-9 after letters if needed.
    keys = [chr(c) for c in range(ord("a"), ord("z") + 1)] + list("0123456789")
    pairs = list(zip(keys, entries))
    print("\nSelect directory:")
    for key, name in pairs:
        print(f"  {key}) {name}")

    sys.stdout.write("Choice: ")
    sys.stdout.flush()
    ch = get_key()
    print(ch)
    for key, name in pairs:
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
            run(["git", "status"])
        elif ch == "2":
            run(["git", "pull"])
        elif ch == "3":
            if sys.platform.startswith("win"):
                run(["cmd", "/c", "dir"])
            else:
                run(["ls"])
        elif ch == "4":
            launch_shell()
        elif ch == "5":
            try:
                os.chdir("..")
                print(f"Moved to parent: {os.getcwd()}")
            except OSError as exc:
                print(f"Could not move to parent: {exc}")
        elif ch == "6":
            choose_directory()
        elif ch == "7":
            git_add_prompt()
        elif ch == "8":
            git_commit_prompt()
        elif ch == "9":
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
