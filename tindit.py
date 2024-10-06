# tindit = tiny editor
import os
import curses
import sys
import json
import platform
import subprocess
import time

class TinyEditor:
    def __init__(self):
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.screen.keypad(True)
        curses.start_color()
        curses.use_default_colors()
        for i in range(1, curses.COLORS):
            curses.init_pair(i, i, -1)
        self.current_file = None
        self.content = []
        self.cursor_y, self.cursor_x = 0, 0
        self.top_line = 0
        self.command_mode = False
        self.command_buffer = []
        self.config = self.load_config()
        self.files = []
        self.selected_file = 0
        self.snippets = self.load_snippets()
        self.snippet_mode = False
        self.snippet_selection = 0
        self.snippet_suggestions = []

    def load_config(self):
        if platform.system() == "Windows":
            config_dir = os.path.join(os.environ["APPDATA"], "tindit")
        else:
            config_dir = os.path.expanduser("~/.config/tindit")
        
        config_file = os.path.join(config_dir, "init.json")
        default_config = {"number": False, "relative_number": False, "tab_is": "SPC", "tab_space_len": 4, "snippets_enabled": True}

        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        if not os.path.exists(config_file):
            with open(config_file, 'w') as f:
                json.dump(default_config, f)
            return default_config

        with open(config_file, 'r') as f:
            config = json.load(f)
            return config

    def load_snippets(self):
        if platform.system() == "Windows":
            config_dir = os.path.join(os.environ["APPDATA"], "tindit")
        else:
            config_dir = os.path.expanduser("~/.config/tindit")
        
        snippets_file = os.path.join(config_dir, "snippets.json")
        default_snippets = {"hello": "print(\"Hello, world!\")\n"}

        if not os.path.exists(snippets_file):
            with open(snippets_file, 'w') as f:
                json.dump(default_snippets, f)
            return default_snippets

        with open(snippets_file, 'r') as f:
            snippets = json.load(f)
            return snippets

    def run(self):
        self.show_file_browser()
        while True:
            if self.current_file:
                self.display_file()
            else:
                self.display_file_browser()
            
            ch = self.screen.getch()
            if ch == 27:  # ESC
                if self.current_file:
                    self.current_file = None
                    self.content = []
                    self.cursor_y, self.cursor_x = 0, 0
                    self.top_line = 0
                else:
                    break
            elif ch == 10:  # Enter
                if self.command_mode:
                    self.execute_command()
                    self.command_mode = False  # Exit command mode after executing command
                elif not self.current_file:
                    self.open_selected_file()
                elif self.snippet_mode:
                    self.expand_snippet()
                    self.snippet_mode = False
                    self.snippet_suggestions = []
                    self.snippet_selection = 0
                else:
                    self.insert_char(ch)
            elif ch == curses.KEY_UP:
                if not self.current_file:
                    self.move_file_selection(-1)
                elif self.snippet_mode:
                    self.move_snippet_selection(-1)
                else:
                    self.move_cursor(-1, 0)
            elif ch == curses.KEY_DOWN:
                if not self.current_file:
                    self.move_file_selection(1)
                elif self.snippet_mode:
                    self.move_snippet_selection(1)
                else:
                    self.move_cursor(1, 0)
            elif ch == curses.KEY_LEFT:
                self.move_cursor(0, -1)
            elif ch == curses.KEY_RIGHT:
                self.move_cursor(0, 1)
            elif ch == curses.KEY_PPAGE:  # Page Up
                self.move_cursor(-curses.LINES + 1, 0)
            elif ch == curses.KEY_NPAGE:  # Page Down
                self.move_cursor(curses.LINES - 1, 0)
            elif ch == curses.KEY_HOME:  # Home
                self.cursor_x = 0
            elif ch == curses.KEY_END:  # End
                if self.cursor_y < len(self.content):
                    self.cursor_x = len(self.content[self.cursor_y].rstrip())
            elif ch == 19:  # CTRL+S
                self.save_file()
            elif ch == curses.KEY_F1:  # F1
                self.command_mode = True
            elif ch == curses.KEY_BACKSPACE or ch == 127:  # Backspace
                if self.command_mode:
                    self.handle_command_backspace()
                else:
                    self.delete_char()
            elif self.command_mode:
                self.handle_command_input(ch)
            elif self.current_file and 32 <= ch <= 126:  # Printable ASCII characters
                self.insert_char(ch)
                if self.config["snippets_enabled"]:
                    self.update_snippet_suggestions()
            elif ch == 9:  # Tab
                if self.config["tab_is"] == "SPC":
                    for _ in range(self.config["tab_space_len"]):
                        self.insert_char(32)
                elif self.config["tab_is"] == "TAB":
                    self.insert_char(9)

            # Ensure the cursor is visible after any key press
            curses.curs_set(1)  # Show the cursor

        self.cleanup()

    def show_file_browser(self):
        self.files = os.listdir('.')
        self.selected_file = 0
        # Add ".." option to go to the parent directory
        if os.path.dirname(os.getcwd()):
            self.files.insert(0, "..")

    def display_file_browser(self):
        self.screen.clear()
        height, width = self.screen.getmaxyx()
        for i, file in enumerate(self.files):
            if i >= height - 1:
                break
            if i == self.selected_file:
                self.screen.addstr(i, 0, f"> {file}", curses.A_REVERSE)
            else:
                self.screen.addstr(i, 0, f"  {file}")
        if self.command_mode:
            self.screen.addstr(height - 1, 0, ":" + "".join(self.command_buffer))
        self.screen.refresh()

    def move_file_selection(self, direction):
        self.selected_file = (self.selected_file + direction) % len(self.files)

    def open_selected_file(self):
        filename = self.files[self.selected_file]
        if filename == "..":  # Go to the parent directory
            os.chdir("..")
            self.show_file_browser()
        elif os.path.isdir(filename):
            os.chdir(filename)
            self.show_file_browser()
        else:
            self.current_file = filename
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    self.content = f.readlines()
            else:
                self.content = ['']
            self.cursor_y, self.cursor_x = 0, 0
            self.top_line = 0

    def display_file(self):
        self.screen.clear()
        height, width = self.screen.getmaxyx()
        status = f" {self.current_file} - Line {self.cursor_y + 1}/{len(self.content)} "
        self.screen.addstr(height - 1, 0, status.ljust(width)[:width - 1], curses.A_REVERSE)

        for i, line in enumerate(self.content[self.top_line:self.top_line + height - 1]):
            line_num = i + self.top_line + 1
            if self.config["number"]:
                if self.config.get("relative_number", False):
                    if line_num == self.cursor_y + 1:
                        self.screen.addstr(i, 0, f"{line_num:4d} ", curses.A_BOLD)
                    else:
                        rel_num = abs(line_num - self.cursor_y - 1)
                        self.screen.addstr(i, 0, f"{rel_num:4d} ", curses.A_DIM)
                else:
                    self.screen.addstr(i, 0, f"{line_num:4d} ", curses.A_DIM)
                start_x = 5
            else:
                start_x = 0

            # Adjusting the display to avoid trailing spaces
            line_display = line.rstrip()  # Remove trailing spaces for display
            self.screen.addstr(i, start_x, line_display[:width - start_x - 1])

        if self.command_mode:
            self.screen.addstr(height - 2, 0, ":" + "".join(self.command_buffer))
        elif self.snippet_mode:
            for i, suggestion in enumerate(self.snippet_suggestions):
                if i >= height - 2:
                    break
                if i == self.snippet_selection:
                    self.screen.addstr(i, 0, f"> {suggestion}", curses.A_REVERSE)
                else:
                    self.screen.addstr(i, 0, f"  {suggestion}")

        cursor_y = self.cursor_y - self.top_line
        cursor_x = self.cursor_x + (5 if self.config["number"] else 0)

        # Ensure cursor position is within bounds before moving
        if 0 <= cursor_y < height - 1 and 0 <= cursor_x < width:
            self.screen.move(cursor_y, cursor_x)
        else:
            # Reset cursor position if out of bounds
            self.cursor_y = min(max(cursor_y, 0), height - 2)
            self.cursor_x = min(max(cursor_x, 0), width - 1)
            self.screen.move(self.cursor_y, self.cursor_x)

        self.screen.refresh()

    def move_cursor(self, dy, dx):
        new_y = max(0, min(len(self.content) - 1, self.cursor_y + dy))
        new_x = max(0, min(len(self.content[new_y].rstrip()) if self.content else 0, self.cursor_x + dx))
        self.cursor_y, self.cursor_x = new_y, new_x

        # Scroll the display if the cursor goes out of bounds
        height, width = self.screen.getmaxyx()
        if self.cursor_y >= self.top_line + height - 1:
            self.top_line = self.cursor_y - height + 2
        elif self.cursor_y < self.top_line:
            self.top_line = self.cursor_y

        self.display_file()

    def insert_char(self, ch):
        if ch == ord('\n'):
            self.content.insert(self.cursor_y + 1, self.content[self.cursor_y][self.cursor_x:])
            self.content[self.cursor_y] = self.content[self.cursor_y][:self.cursor_x] + '\n'
            self.cursor_y += 1
            self.cursor_x = 0
        else:
            if not self.content:
                self.content = ['']
            line = self.content[self.cursor_y]
            self.content[self.cursor_y] = line[:self.cursor_x] + chr(ch) + line[self.cursor_x:]
            self.cursor_x += 1

    def delete_char(self):
        if self.cursor_x > 0:
            line = self.content[self.cursor_y]
            self.content[self.cursor_y] = line[:self.cursor_x - 1] + line[self.cursor_x:]
            self.cursor_x -= 1
        elif self.cursor_y > 0:
            self.cursor_y -= 1
            self.cursor_x = len(self.content[self.cursor_y].rstrip())
            self.content[self.cursor_y] = self.content[self.cursor_y].rstrip() + self.content.pop(self.cursor_y + 1)

    def save_file(self):
        with open(self.current_file, 'w') as f:
            f.writelines(self.content)

    def handle_command_input(self, ch):
        if ch == 27:  # ESC
            self.command_mode = False
            self.command_buffer = []
        elif 32 <= ch <= 126:  # Printable ASCII characters
            self.command_buffer.append(chr(ch))

    def handle_command_backspace(self):
        if self.command_buffer:
            self.command_buffer.pop()

    def execute_command(self):
        command = "".join(self.command_buffer).strip().split()
        if not command:
            self.command_mode = False
            self.command_buffer = []
            return

        if command[0] == "save":
            self.save_file()
        elif command[0] == "create" and len(command) > 1:
            filename = command[1]
            open(filename, 'a').close()  # Create an empty file
            self.files = os.listdir('.')  # Refresh file list
            self.show_file_browser()  # Show updated file browser
            self.screen.addstr(curses.LINES - 2, 0, f"File '{filename}' created successfully")
            self.screen.refresh()
            curses.napms(2000)
        elif command[0] == "mkdir" and len(command) > 1:  # Create a new directory
            dirname = command[1]
            os.makedirs(dirname, exist_ok=True)
            self.files = os.listdir('.')  # Refresh file list
            self.show_file_browser()  # Show updated file browser
            self.screen.addstr(curses.LINES - 2, 0, f"Directory '{dirname}' created successfully")
            self.screen.refresh()
            curses.napms(2000)
        elif command[0] == "exit":
            self.cleanup()
            sys.exit(0)
        elif command[0] == "number":
            self.config["number"] = not self.config["number"]
            self.save_config()
        elif command[0] == "relativenumber":
            if self.config["number"]:
                self.config["relative_number"] = not self.config["relative_number"]
                self.save_config()
            else:
                self.screen.addstr(curses.LINES - 2, 0, "Error: 'number' must be enabled for 'relativenumber'")
                self.screen.refresh()
                curses.napms(2000)
        elif command[0] == "explosion":
            self.trigger_explosion()
        elif command[0] == "com":
            self.execute_terminal_command()
            self.command_mode = False  # Reset command mode after executing command
            self.command_buffer = []   # Clear command buffer
            # Ensure cursor is within bounds after terminal command execution
            if self.content:  # Check if content is not empty
                self.cursor_y = min(self.cursor_y, len(self.content) - 1)  # Ensure cursor is within bounds
                self.cursor_x = min(self.cursor_x, len(self.content[self.cursor_y].rstrip()) if self.cursor_y < len(self.content) else 0)  # Ensure cursor is within line
            self.display_file()  # Refresh display after returning from command mode
        elif command[0] == "rmdir" and len(command) > 1:  # Remove a directory
            dirname = command[1]
            try:
                os.system("rm -rf {}".format(dirname))
                self.files = os.listdir('.')  # Refresh file list
                self.show_file_browser()  # Show updated file browser
                self.screen.addstr(curses.LINES - 2, 0, f"Directory '{dirname}' removed successfully")
                self.screen.refresh()
                curses.napms(2000)
            except OSError as e:
                self.screen.addstr(curses.LINES - 2, 0, f"Error: {e}")
                self.screen.refresh()
                curses.napms(2000)
        elif command[0] == "rmfile" and len(command) > 1:  # Remove a file
            filename = command[1]
            try:
                os.remove(filename)
                self.files = os.listdir('.')  # Refresh file list
                self.show_file_browser()  # Show updated file browser
                self.screen.addstr(curses.LINES - 2, 0, f"File '{filename}' removed successfully")
                self.screen.refresh()
                curses.napms(2000)
            except OSError as e:
                self.screen.addstr(curses.LINES - 2, 0, f"Error: {e}")
                self.screen.refresh()
                curses.napms(2000)

    def trigger_explosion(self):
        height, width = self.screen.getmaxyx()
        center_y, center_x = self.cursor_y, self.cursor_x
        radius = 1
        speed = 0.1  # Increased speed for the explosion effect

        # Create explosion effect
        while radius < max(height, width):
            self.screen.clear()
            for y in range(height):
                for x in range(width):
                    if (y - center_y) ** 2 + (x - center_x) ** 2 <= radius ** 2:
                        if y < len(self.content):  # Check if within content bounds
                            self.screen.addstr(y, x, " ", curses.A_REVERSE)
                    else:
                        if y < len(self.content):
                            line_display = self.content[y].rstrip()
                            self.screen.addstr(y, 0, line_display[:width])
            self.screen.refresh()
            time.sleep(speed)  # Use the new speed variable
            radius += 2  # Increase the radius more quickly

        # Characters start to reappear
        time.sleep(2)

        # Move content to the bottom
        self.screen.clear()
        for i in range(len(self.content)):
            if i < height - 5:
                self.screen.addstr(min(height - 5 + i, height - 1), 0, self.content[i].rstrip())
        
        self.screen.addstr(height - 1, 0, "Characters have fallen to the bottom!")
        self.screen.refresh()
        time.sleep(5)

        # Reset the display
        self.screen.clear()
        self.display_file()
        self.screen.addstr(height - 1, 0, "Explosion effect completed!")
        self.screen.refresh()
        time.sleep(2)

    def execute_terminal_command(self):
        curses.echo()
        curses.curs_set(1)
        height, width = self.screen.getmaxyx()
        self.screen.addstr(height - 2, 0, "Enter command: ")
        self.screen.refresh()
        command = self.screen.getstr(height - 2, 16).decode('utf-8')
        
        try:
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            output = e.output
        
        self.screen.clear()
        self.screen.addstr(0, 0, "Command output:")
        for i, line in enumerate(output.split('\n')):
            if i >= height - 3:
                break
            self.screen.addstr(i + 1, 0, line[:width - 1])
        
        self.screen.addstr(height - 1, 0, "Press any key to continue...")
        self.screen.refresh()
        self.screen.getch()
        
        curses.noecho()
        curses.curs_set(0)

    def save_config(self):
        if platform.system() == "Windows":
            config_file = os.path.join(os.environ["APPDATA"], "tindit", "init.json")
        else:
            config_file = os.path.expanduser("~/.config/tindit/init.json")
        with open(config_file, 'w') as f:
            json.dump(self.config, f)

    def handle_snippet_expansion(self):
        if self.current_file:
            current_line = self.content[self.cursor_y].rstrip()
            for snippet_name, snippet_content in self.snippets.items():
                if current_line.endswith(snippet_name):
                    # Split the snippet content into lines
                    snippet_lines = snippet_content.splitlines()
                    # Calculate the insertion point for each line
                    insertion_point = self.cursor_y
                    for i, line in enumerate(snippet_lines):
                        self.content.insert(insertion_point + i + 1, line)
                    # Replace the snippet name with the first line of the snippet
                    self.content[self.cursor_y] = current_line.replace(snippet_name, snippet_lines[0], 1)
                    # Adjust cursor position
                    self.cursor_y += len(snippet_lines) - 1
                    self.cursor_x = len(self.content[self.cursor_y].rstrip())
                    self.display_file()
                    break

    def update_snippet_suggestions(self):
        if self.config["snippets_enabled"]:
            current_line = self.content[self.cursor_y].rstrip()
            self.snippet_suggestions = [
                snippet_name for snippet_name in self.snippets
                if current_line.endswith(snippet_name) or snippet_name.startswith(current_line)
            ]
            if self.snippet_suggestions:
                self.snippet_mode = True
                self.snippet_selection = 0
            else:
                self.snippet_mode = False
                self.snippet_suggestions = []
                self.snippet_selection = 0

    def move_snippet_selection(self, direction):
        self.snippet_selection = (self.snippet_selection + direction) % len(self.snippet_suggestions)

    def expand_snippet(self):
        if self.snippet_suggestions:
            snippet_name = self.snippet_suggestions[self.snippet_selection]
            snippet_content = self.snippets[snippet_name]
            # Insert snippet content into the file character by character
            self.content[self.cursor_y] = ""
            for char in snippet_content:
                if char == '\n':
                    self.content.insert(self.cursor_y + 1, self.content[self.cursor_y][self.cursor_x:])
                    self.content[self.cursor_y] = self.content[self.cursor_y][:self.cursor_x] + '\n'
                    self.cursor_y += 1
                    self.cursor_x = 0
                else:
                    self.content[self.cursor_y] += char
                    self.cursor_x += 1
                self.display_file()
            # Adjust cursor position
            self.cursor_x = len(self.content[self.cursor_y].rstrip())
            # Update the display
            self.display_file()

    def cleanup(self):
        curses.nocbreak()
        self.screen.keypad(False)
        curses.echo()
        curses.endwin()

if __name__ == "__main__":
    editor = TinyEditor()
    editor.run()
