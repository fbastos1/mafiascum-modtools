from bs4 import BeautifulSoup
import requests
from ruamel.yaml import YAML
import jellyfish
import logging
import coloredlogs
import argparse

JARO_WINKLER_ACCEPT_THRESHOLD = 0.88
JARO_WINKLER_WARN_THRESHOLD = 0.95
NO_EXEC_VOTES = [
    'no execution',
    'no lynch',
    'no elimination',
    'no elim'
]
UNVOTE_VOTES = [
    'unvote',
    '',
]
logger = logging.getLogger('votecounter')


class UnresolvedVoteError(Exception):
    """Exception raised when a vote cannot be resolved by alias
    resolution + fuzzy matching

    Attributes:
        unresolved_target -- the vote target, as written in the post
        post_number -- the post number for the vote
        post_author -- the post author for the vote
    """

    def __init__(self, unresolved_target, post_number, post_author):
        self.unresolved_target = unresolved_target
        self.post_number = post_number
        self.post_author = post_author

        self.message = (
            f'Unresolved vote in #{self.post_number}: '
            f'{self.post_author} -> {self.unresolved_target}'
        )
        super().__init__(self.message)

    def __repr__(self):
        return self.message


def recursive_resolve_alias(player, aliases):
    """Resolves an alias to a player's name.

    Args:
        player -- the alias to be resolved. Case insensitive.
        aliases -- list of aliases in the game, to include replacements. Must contain identifiers in lowercase

    Returns:
        str -- the resolved alias.
    """
    if player is None:
        return None
    while player.lower() in aliases:
        player = aliases[player.lower()]
    return player


def fuzzy_match_alias(
        player,
        aliases,
        players,
        replacements,
        similarity_f,
):
    """performs fuzzy matching.

    Args:
        player -- the name to be resolved. must be lowercase.
        aliases -- the dictionary of known aliases for players in the game.
        players -- the list of players in the game.
        replacements -- the dictionary of replacements in the game.
        similarity_f -- function to take two strings and return a numeric similarity

    Returns:
        tuple with (closest match, similarity value)
    """
    identifier_list = []
    for alias_source in (players, *aliases.values(), *replacements.values()):
        identifier_list.extend(map(str.lower, alias_source))

    return max(
        [
            (_id, similarity_f(player, _id))
            for _id in identifier_list
        ],
        key=lambda t: t[1]
    )


def last_action_index(action, actions):
    """Returns the index for the last instance of an action in actions

    Args:
        action -- str, the action to be found
        actions -- list of tuples, where t[0] is the action and t[1] is the target

    Returns:
        int for last instance of a given action in actions, if found. -1 otherwise
    """
    try:
        return max(idx for idx, val in enumerate(actions) if val[0] == action)
    except ValueError:
        return -1


def resolve_vote(vote, players_lower, aliases, replacements, ignores, literal_match_only=False, ignore_aliases=False):
    """Resolves a vote/unvote

    Args:
        vote -- dictionary with values for voter, target, post_number, and post_url
        players_lower -- lowercase list of players in the game
        aliases -- dictionary mapping player names to lists of aliases
        replacements -- dictionary mapping replacements to lists of replaced players

    Returns:
        vote, with vote['voter'] resolved to be a player in the game or None (for unvote)
    """
    if vote['target'] and vote['target'].lower() in ignores:
        return {}

    alias_map = {}
    for reverse_alias_source in aliases.items(), replacements.items():
        for k, v in reverse_alias_source:
            alias_map.update(
                {alias.lower(): k.lower() for alias in v}
            )

    vote['voter'] = recursive_resolve_alias(vote['voter'].lower(), alias_map)
    if vote['voter'].lower() not in players_lower:
        return vote

    if vote['target'] is None:
        logger.debug('{}: {} -> {}'
                     .format(
                         vote['post_number'],
                         vote['voter'],
                         vote['target'],
                     ))
        return vote

    vote['target'] = vote['target'].lower()

    if vote['target'] not in players_lower and vote['target'] not in alias_map:
        if literal_match_only:
            logger.critical(
                'Could not resolve {}\'s vote in #{}: {} is not in player list.'
                .format(vote['voter'], vote['post_number'], vote['target'])
            )
            raise UnresolvedVoteError(vote['target'], vote['post_number'], vote['voter'])

        logger.info(
            'Player {} voted {} in #{}, but target is not in aliases. Attempting fuzzy matching'
            .format(vote['voter'], vote['target'], vote['post_number'])
        )
        vote_target, confidence = fuzzy_match_alias(
            vote['target'], aliases, players_lower, replacements,
            similarity_f=jellyfish.jaro_winkler_similarity
        )
        if confidence < JARO_WINKLER_ACCEPT_THRESHOLD:
            logger.critical(
                'Could not resolve {}\'s vote in #{}: confidence too low. ({} -> {}, conf: {})'
                .format(
                    vote['voter'], vote['post_number'], vote['target'],
                    vote_target, confidence
                )
            )
            raise UnresolvedVoteError(vote['target'], vote['post_number'], vote['voter'])
        elif confidence < JARO_WINKLER_WARN_THRESHOLD:
            logger.warning(
                'Resolved {}\'s vote in #{} with low confidence: {} -> {}, conf: {}'
                .format(
                    vote['voter'], vote['post_number'], vote['target'],
                    vote_target, confidence
                )
            )
        else:
            logger.info(
                'Resolved {}\'s vote in #{}: {} -> {}, conf: {}'
                .format(
                    vote['voter'], vote['post_number'], vote['target'],
                    vote_target, confidence
                )
            )

        vote['target'] = vote_target

    if ignore_aliases and vote['target'] not in players_lower:
        raise UnresolvedVoteError(vote['target'], vote['post_number'], vote['voter'])
        
    vote['target'] = recursive_resolve_alias(vote['target'], alias_map)
    logger.debug('{}: {} -> {}'
                 .format(
                     vote['post_number'],
                     vote['voter'],
                     vote['target'],
                 ))

    return vote


def get_page_votes(url, params=None, page=1):
    """returns page votes for a given URL

    Args:
        url -- string for the page to parse
        params -- dictionary of params to make the request with (typically,
                  this is the thread id; e.g., {'t': '12345'})
        page -- the number of the page to parse

    Returns:
        list containing dictionaries for each vote (with voter, target, post_number, post_url)
    """
    ret = []
    params['start'] = (page-1)*25

    rq = requests.get(url, params=params)
    soup = BeautifulSoup(rq.text, 'html.parser')
    for post in soup.find_all('div', {'class': 'post'}):
        profile = post.find('dl', {'class': 'postprofile'})
        try:
            username = profile.find('a', {'class': 'username'}).text
        except AttributeError:
            # the fucking mods break the votecounter!!!
            username = profile.find('a', {'class': 'username-coloured'}).text
        post_number = post.find('span', {'class': 'post-number-bolded'}).text[1:]
        post_url = post.find('a', {'class': 'unread'}, href=True)['href'][1:]
        post_content = post.find('div', {'class': 'content'})

        ignored_tags = ('blockquote', 'quotecontent')
        for tag in ignored_tags:
            for element in post_content.find_all(tag):
                element.extract()

        actions = list(
            map(
                lambda v: tuple(map(str.strip, v.string.split(':'))),
                post_content.find_all(
                    'span',
                    {'class': 'bbvote'})
            )
        )

        if not actions:
            continue

        #  handle the stupid "VOTE: unvote"
        for i in range(len(actions)):
            if actions[i][0] == 'VOTE' and actions[i][1].lower() in UNVOTE_VOTES:
                actions[i] = ('UNVOTE', None)

        #  TODO: make this not garbage
        number_of_votes = tuple(map(lambda t: t[0], actions)).count('VOTE')
        last_target = actions[-1][1] if actions[-1][0] == 'VOTE' else None
        last_vote_idx = last_action_index('VOTE', actions)
        last_unvote_idx = last_action_index('UNVOTE', actions)

        if number_of_votes > 1:
            logger.warning(
                f'{username} voted twice for multiple players in '
                f'#{post_number}; defaulting to last vote ({last_target})'
            )
        elif -1 < last_vote_idx < last_unvote_idx:
            logger.warning(
                f'{username} unvoted after voting for {actions[last_vote_idx][1]} '
                f'in #{post_number}; defaulting to unvote'
            )

        if (actions):
            action, target = actions[-1]
            ret.append({
                'voter': username,
                'target': None if action == 'UNVOTE' else target,
                'post_number': post_number,
                'post_url': post_url,
            })

    return ret


def get_page_count(url, params):
    """Returns the number of pages for a thread

    Args:
        url -- the URL to make the request to
        params -- the params for the request (typically, this includes a thread ID)

    Returns:
        int, number of pages in thread
    """
    rq = requests.get(url, params=params)
    soup = BeautifulSoup(rq.text, 'html.parser')

    try:
        # horrible hack. fix later
        # may completely break if there is only 1 page lol
        return int(soup.find('div', {'class': 'pagination'}).text.split()[-2])
    except AttributeError:
        return 1


def parse_game_yaml(filename):
    """Parses a game definition as given in a yaml file.

    Args:
        filename -- str for the path to the file

    Returns:
        dictionary containing players, aliases, replacements, game url, and url params
    """
    try:
        with open(filename, 'r') as f:
            yaml = YAML(typ='safe')
            return yaml.load(f)
    except FileNotFoundError:
        logger.critical('could not find game file {}'.format(filename))


def count_votes(game_definition, start=None, end=None, **kwargs):
    """counts the votes for a game.

    Args:
        game_definition -- the game definition, as parsed by `parse_game_yaml`
        start -- optional; number post to start counting from. inclusive
        end -- optional; number post to end counting at. inclusive

    Returns:
        dictionary containing boolean for hammer, list of votes, and number of votes for each player
    """
    coloredlogs.install(level=logger.getEffectiveLevel(), logger=logger)

    players = game['players']
    aliases = game['aliases']
    replacements = game['replacements']
    ignores = game['ignore']

    game_url = game['game']['base_url']
    params = game['game']['params']

    votes = {
        player.lower(): {
            'voter': player,
            'target': None,
            'post_url': None,
            'post_number': None
        }
        for player in players
    }
    page_count = get_page_count(game_url, params)
    vote_counts = {player.lower(): 0 for player in players}

    *players_lower, = map(str.lower, players)
    for v in replacements.values():
        players_lower.extend(map(str.lower, v))

    logger.info('getting pages {} to {}'.format(1, page_count))

    if start is None:
        start = 0
    if end is None:
        end = page_count * 25

    hammer = False
    for pg in range(start//25, page_count):
        logger.debug('-- page {} --'.format(pg+1))
        for vote in map(
                lambda d: {
                    **resolve_vote(
                        d,
                        tuple(map(str.lower, players)),
                        aliases,
                        replacements,
                        ignores,
                        **kwargs
                    )},
                get_page_votes(game_url, params, pg+1)
        ):
            if not vote or int(vote['post_number']) < start or vote['voter'] not in players_lower:
                continue

            if int(vote['post_number']) > end:
                return {
                    'hammer': hammer,
                    'votes': votes,
                    'vote_counts': vote_counts,
                }

            try:
                vote_counts[votes[vote['voter']]['target']] -= 1
            except KeyError:
                if votes[vote['voter']]['target'] is not None:
                    logger.warning(
                        'tried to decrement count voter after vote ({} -> {}), but {} is not in vote_counts.'
                        .format(vote['voter'], vote['target'], votes[vote['voter']]['target'])
                    )
            votes[vote['voter']] = vote
            if vote['target'] is not None:
                vote_counts[vote['target']] += 1

            hammer = max(vote_counts.values()) > len(players)//2

            if hammer and not kwargs.get('ignore_hammer'):
                return {
                    'hammer': hammer,
                    'votes': votes,
                    'vote_counts': vote_counts,
                }

    return {
        'hammer': hammer,
        'votes': votes,
        'vote_counts': vote_counts,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', '-s', type=int, help='the starting post to count from', default=None)
    parser.add_argument('--end', '-e', type=int, help='the ending post to count to', default=None)
    parser.add_argument('--log-level', type=str,
                        help='the logging level for the votecounter', default='INFO',
                        choices=[f(s) for s in ['info', 'debug', 'warning', 'error'] for f in (lambda s:s.lower(), lambda s:s.upper())])

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--no-fuzzy-match', help='disables fuzzy matching', action='store_true')
    group.add_argument('--no-alias-resolution', help='disables alias matching', action='store_true')
    parser.add_argument('--ignore-hammer', help='continues the vote count after hammer', action='store_true')

    parser.add_argument('game_definition_yaml', help='path to the game definition file')

    args = parser.parse_args()

    logger.setLevel(args.log_level.upper())

    parsing_options = {}
    if args.no_fuzzy_match:
        parsing_options['literal_match_only'] = True
    if args.no_alias_resolution:
        parsing_options['ignore_aliases'] = True
        parsing_options['literal_match_only'] = True
    if args.ignore_hammer:
        parsing_options['ignore_hammer'] = True

    game = parse_game_yaml(args.game_definition_yaml)
    try:
        res = count_votes(game, start=args.start, end=args.end, **parsing_options)
    except UnresolvedVoteError as e:
        logger.critical(f'Could not complete vote counting! UnresolvedVoteError: {e}')
        exit(1)

    print('hammer? {}'.format(res['hammer']))
    vote_targets = {player: [] for player in res['votes']}
    vote_targets[None] = []

    for vote in res['votes'].values():
        print('[{}] {} -> {}'.format(vote['post_number'], vote['voter'], vote['target']))
        vote_targets[vote['target']].append(vote)

    player_case_map = {player.lower(): player for player in game['players']}
    player_case_map[None] = 'Not voting'

    print('\n\tFINAL VOTE COUNT:\n')
    for player, vote_list in sorted(vote_targets.items(), key=lambda t: len(t[1]), reverse=True):
        try:
            player = player_case_map[player]
        except KeyError:
            pass  # player already cased correctly
        vote_strings = []
        try:
            vote_list = sorted(vote_list, key=lambda d: d['post_number'])
        except TypeError:
            pass  # comparing None, in case players haven't voted yet
        for vote in vote_list:
            if vote['post_url'] is not None:
                vote_strings.append(
                    '[url=https://forum.mafiascum.net{}]{} [size=75]({})[/size][/url]'
                    .format(vote['post_url'], vote['voter'], vote['post_number']))
            else:
                vote_strings.append(vote['voter'])

        print('[b]{}[/b] ({}): {}'.format(player, len(vote_strings), ', '.join(vote_strings)))
