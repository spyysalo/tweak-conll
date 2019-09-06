#!/usr/bin/env python3

import sys
import re

from itertools import cycle, islice


QUOTES = set(['"'])


def argparser():
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument('-t', '--token', default=1, type=int,
                    help='index of token text field (1-based)')
    ap.add_argument('-i', '--index', default=2, type=int,
                    help='index of field to tweak (1-based)')
    ap.add_argument('data', nargs='+',
                    help='CoNLL-formatted tagged data')
    return ap


def roundrobin(*iterables):
    """roundrobin('ABC', 'D', 'EF') --> A D E B F C"""
    # Recipe credited to George Sakkis (via itertools recipes)
    num_active = len(iterables)
    nexts = cycle(iter(it).__next__ for it in iterables)
    while num_active:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            # Remove the iterator we just exhausted from the cycle.
            num_active -= 1
            nexts = cycle(islice(nexts, num_active))


def interleave(list1, list2):
    return list(roundrobin(list1, list2))


def is_start(prev_tag, curr_tag, next_tag):
    return curr_tag.startswith('B-')


def is_end(prev_tag, curr_tag, next_tag):
    return ((curr_tag.startswith('B-') or curr_tag.startswith('I-')) and
            (next_tag in (None, 'O') or next_tag[2:] != curr_tag[2:]))


def tweak_quotes(toks, tags, options):
    assert len(toks) == len(tags)
    tweaked = []
    mi, sentry = len(tags)-1, (None, None)
    prev_was_startquote = False
    for i in range(len(tags)):
        prev_tok, prev_tag = (toks[i-1], tags[i-1]) if i > 0 else sentry
        tok, tag = toks[i], tags[i]
        next_tok, next_tag = (toks[i+1], tags[i+1]) if i+1 < mi else sentry
        is_startquote = False
        if tok in QUOTES:
            if (is_start(prev_tag, tag, next_tag) and
                not is_end(prev_tag, tag, next_tag)):
                is_startquote = True
                tag = 'O'
            elif (is_end(prev_tag, tag, next_tag) and
                  not is_start(prev_tag, tag, next_tag)):
                tag = 'O'
        if prev_was_startquote:
            tag = prev_tag    # propagate B- tag on quote
        tweaked.append(tag)
        prev_was_startquote = is_startquote
    return tweaked


def process_sentence(fields, spaces, options):
    tokens = [f[options.token-1] for f in fields]
    for index in [options.index-1]:
        values = [f[index] for f in fields]
        values = tweak_quotes(tokens, values, options)
        fields = [f[:index]+[v]+f[index+1:] for f, v in zip(fields, values)]
    for f, s in zip(fields, spaces):
        print(''.join(interleave(f, s)))


def process(fn, options):
    with open(fn) as f:
        sent_fields, sent_spaces = [], []
        for ln, l in enumerate(f, start=1):
            l = l.rstrip('\n')
            if l.isspace() or not l:
                process_sentence(sent_fields, sent_spaces, options)
                sent_fields, sent_spaces = [], []
                print(l)
            else:
                fields_and_spaces = re.split(r'(\s+)', l)
                fields = fields_and_spaces[::2]
                spaces = fields_and_spaces[1::2]
                assert fields_and_spaces == interleave(fields, spaces)
                sent_fields.append(fields)
                sent_spaces.append(spaces)
        if sent_fields:
            process_sentence(sent_fields, sent_spaces, options)


def main(argv):
    args = argparser().parse_args(argv[1:])
    for fn in args.data:
        process(fn, args)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
