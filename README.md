# tindit
open source terminal code editor made with AI (i made this because i like to create projects with ai :D)

## quick start
open the editor using
```console
$ python3 tindit.py
```

open the command bar using F1.<br>
simple commands:
```command
save          -- save the cw file
explosion     -- simple explosion animation (only works while editing a file)
mkdir <name>  -- creates a folder in your cwd
rmdir <name>  -- removes a folder in your cwd
rmfile <name> -- removes a file in your cwd
create <name> -- creates a file in your cwd
```

to exit the file you're editing, press ESC (ESCAPE) and to edit the editor, press ESC in the file explorer<br>
the tindit configurations file path is in ~/.config/tindit/init.json and in windows is in %APPDATA%\tindit\init.json<br>
first open the editor to create the configuration file!<br>
in your configuration file you'll see the configuration "tab_is", by default it will have the value of 'SPC', if you press tab it will add the amout of spaces that the configuration "tab_space_len" is. if you use "tab_is": "TAB" it will only add one TAB (\t)
