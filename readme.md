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

Required keys are marked in __bold__, and optional keys are in __italic__; sub-keys are indented below their parent key.

- __game__, dictionary
  - __base_url__, string: base URL for the game. For the current version of phpBB Mafiascum runs on, changing this should not be necessary.
  - __params__, dictionary: url parameters to be used with __base_url__. Typically, only thread ID goes here.
- __players__, list: list of players in the game
- _aliases_, dictionary: should contain lists of aliases for each player, keyed on player name
  - _[player name]_, list: MUST be in __players__. Contains aliases that map to _[player name]_.
- _replacements_, dictionary: should contain lists of replacements for each player, keyed on player name
  - _[player name]_, list: MUST be in __players__. Contains players that were replaced by _[player name]_, either directly or indirectly (i.e., if a slot was replaced twice, both names should be here).
- _ignore_, list: list of votes to explicitly ignore.

Note that when a player is replaced, a key must be added for them under _replacements_ and the __players__ list should reflect the name of the new player (i.e., the __players__ list should _always_ be kept up to date).

---

##### formatter

_An example of a jinja template can be found in osuka.jinja._

The following template parameters are available in a jinja template:
- __player_votes__: list; contains dictionaries, each representing a player. Sorted by number of votes, decreasing. Each dictionary contains two keys:
  - __name__: string; the name of the _target_ player (i.e., the player being voted);
  - __votes__: list; contains dictionaries, each representing a vote. Sorted by post number, increasing. Each dictionary contains the following keys:
    - __post_url__: string; a permalink to the post where the vote was cast
    - __voter__: string; the name of the _voting_ player
    - __post_number__: string; the number of the post where the vote was cast
- __no_execution__: list; contains dictionaries, each representing a vote for a no-execution. Each dictionary contains the following keys:
  - __post_url__: string; a permalink to the post where the vote was cast
  - __voter__: string; the name of the voting player
  - __post_number__: string; the number of the post where the vote was cast
- __not_voting__: list; contains dictionaries, each representing a player. Sorted by post number (if any), increasing. Each dictionary is guaranteed to contain the __voter__ key, but __post_url__ and __post_number__ only exist if the player explicitly unvoted (as opposed to never having voted at all):
  - __voter__: string; the name of the non-voting player
  - _post_url_: string; may not exist; a permalink to the post where the player unvoted, if it exists
  - _post_number_: string; may not exist; the number of the post where the player unvoted, if it exists
