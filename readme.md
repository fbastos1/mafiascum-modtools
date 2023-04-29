# osuka's mod tools documentation
## votecounter

##### description

<pre>votecounter.py [OPTIONS] [PATH TO GAMEDEF FILE]</pre>

<pre>votecounter.py</pre> counts the votes for a given game and outputs a tally of the votes. By default, the
output is not BBCode-formatted.

---

##### dependencies

- ruamel.yaml
- jellyfish
- coloredlogs
- requests
- bs4
- jinja2

---

##### setup

This is a command-line utility with no graphical interface. As such, the user is expected to be able to run the script from a shell.

The recommended way of fetching the source is through `git clone`. If you don't have git installed, you can download the archived repo from the Github web UI or install git with your preferred package manager. [Chocolatey](https://chocolatey.org/) on Windows and [Homebrew](https://brew.sh/) on macOS are popular choices.

After pulling the source and installing git and python3, install the python dependencies:
```
python3 -m pip install ruamel.yaml jellyfish coloredlogs requests bs4 jinja2
```

If you have a file definition (and optionally, a Jinja template), you're ready to run the votecounter.

---

##### options

<i>Options in italic are currently unsupported and may be unimplemented.</i>

<pre><strong>--start=[WHEN]</strong></pre>
Set the starting post for the count. Inclusive. Must be equal to or greater than zero.

<pre><strong>--end=[WHEN]</strong></pre>
Set the ending post for the count. Inclusive. Must be equal to or greater than zero. If `end` is greater than the number of posts
in the thread, all posts will be counted.

<pre><strong>--template [PATH TO JINJA2 TEMPLATE FILE]</strong></pre>
Specifies a Jinja2 template file to read the format output definition from. For details, see the Formatter section.

<pre><strong><i>--parse-only</i></strong></pre>
Run the votecounter as a parser (i.e., votes will not be counted). 

<pre><strong>--no-fuzzy-match</strong></pre>
Only match player names exactly as spelled in the game definition, or as found in the aliases list.

<pre><strong>--no-alias-resolution</strong></pre>
Only match player names as found in the player list. This option ignores the aliases list. If used without `--no-fuzzy-match`,
fuzzy matching is still supported but will not match any names listed as aliases. <b>Implies `--no-fuzzy-match`.</b>

<pre><strong>--ignore-hammer</strong></pre>
If set, will count until `end` regardless of whether an execution was achieved.

<pre><strong>--log-level=[LEVEL]</strong></pre>
Set the log level for the votecounter. Defaults to INFO. Valid inputs are DEBUG, INFO, WARNING, and ERROR.

---

##### game definition

The votecounter requires a game definition file to correctly parse a game. An example is as follows:

```yaml
game:
  base_url: https://forum.mafiascum.net/viewtopic.php
  params:
    t: 86587

players:
  - bugspray
  - T3
  - Anya
  - VFP
  - geraintm
  - Ivyeo
  - Egix96
  - osuka
  - humaneatingmonkey
  - Dunnstral
  - InsidiousLemons
  - Umlaut

aliases:
  bugspray:
    - bug
    - bs
  geraintm:
    - gerain
  Ivyeo:
    - ivy
  Egix96:
    - egix
  humaneatingmonkey:
    - hem
    - humaneating monkey
    - monkeyhuman
    - monkeyeater
  Dunnstral:
    - dunn
  InsidiousLemons:
    - lemons
  Andante:
    - anda

# this means VFP replaced andante, and humaneatingmonkey replaced choof
replacements:
  VFP:
    - Andante
  humaneatingmonkey:
    - choof

# add this to explicitly ignore a vote - in this case, someone voted for the mod
ignore:
  - cook

```

---

##### formatter

todo, whoops. look at the example lol
